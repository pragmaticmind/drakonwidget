#!/usr/bin/env python3
"""Convert DRAKON Editor .drn diagrams from drawn geometry to a graph.

A .drn file is an SQLite database. Each diagram is stored as drawn geometry:
icons with a centre and half-sizes, and separate horizontal, vertical and arrow
line items. This module turns that geometry into the DrakonWidget/DrakonTech
JSON model (items linked by "one"/"two"), the format used by the rest of the
test corpus and by prototypes/text-syntax/dump.py.

It is a port of DRAKON Editor's own pipeline (pragmaticmind/drakon_editor,
a fork of stepan-mitkin/drakon_editor):

  stage 1  scripts/graph2.tcl  extract.manhattan
           Cut lines at icons and at each other, merge collinear pieces,
           attach line ends to icon sides, add knots where lines meet.
  stage 2  scripts/auto.tcl    p.do_extract_auto
           Walk the knots and lines into ordered logical links (down, right,
           case steps, arrow loops, addresses), build branches, check the
           DRAKON rules, pair loops, and skip knots.
  stage 3  generators/drakon_tech.tcl  convert_diagram
           Write the DrakonTech/DrakonWidget items.

Each diagram is converted on its own. A diagram that breaks a rule gets the
same error messages DRAKON Editor would show, and no "drakon" output.

Deliberate differences from the Tcl original (all marked "FIX" below):
  - Branches are numbered left to right by x. The original numbers them in
    Tcl hash-table order, so branchId order can be scrambled.
  - branchId comes from the branch itself. The original looks it up through
    the icon below the header, which fails when that is a knot.
  - The start icon of a silhouette is always left out. The original leaves
    it out only when branch 1 happens to be the one under it.
  - Arrow loops are resolved through the knots they pass, so two arrow loops
    entering one after the other become a chain (outer -> inner -> icon).
    The original points the outer one at "" and sends every loop-back to
    the last arrow item.
  - The loop-entry check is memoised; the original can take exponential time.
These are counted and listed by oracle/compare_reference.py.

By default two things the DrakonTech exporter throws away are kept, because
DrakonWidget supports them: insertion/input/output/process icons keep their
type (the exporter turns them into plain actions), and an icon's second text
(text2, e.g. the second half of a shelf) becomes "secondary". Pass
official=True (or --official) to reproduce the exporter's output exactly.

Usage:
  drn2graph.py [--official] FILE.drn [FILE.drn ...]          one JSON object per diagram
  drn2graph.py [--official] --pretty FILE.drn DIAGRAM_NAME   one diagram, widget JSON only

No dependencies outside the Python standard library.
"""
import json
import os
import sqlite3
import sys
from urllib.request import pathname2url

sys.setrecursionlimit(20000)

# Arrow-head codes stored in the "a" column of line items (icon.links.tcl).
ARROW_NAMES = {
    10100: "up arrow", 20100: "right arrow", 30100: "down arrow", 40100: "left arrow",
    10200: "up white arrow", 20200: "right white arrow", 30200: "down white arrow", 40200: "left white arrow",
    10300: "up paw", 20300: "right paw", 30300: "down paw", 40300: "left paw",
    50100: "parallel",
}
# 1 when the head is at the low end of the line (top or left).
POINTS_UP = {
    10100: 1, 20100: 0, 30100: 0, 40100: 1,
    10200: 1, 20200: 0, 30200: 0, 40200: 1,
    10300: 1, 20300: 0, 30300: 0, 40300: 1,
    50100: 0,
}
PARALLEL = 50100
LEFT_ARROW = 40100
RIGHT_ARROW = 20100

END_TEXTS = ("end", "\u043a\u043e\u043d\u0435\u0446")  # "end", Russian "конец"
ITEM_COLUMNS = ["item_id", "type", "text", "text2", "x", "y", "w", "h", "a", "b"]


class ConversionError(Exception):
    """An internal failure. The Tcl original raises an error in the same place."""


# When an icon swallows every segment at one x (or y), Tcl's merge.on.1.line
# turns the empty list into a list with one empty element. That element then
# behaves like a line whose coordinates are all "": crossing lines that span
# its coordinate drop it; otherwise it becomes a knot at ("", "") that is
# connected to nothing, and the diagram fails the connectivity check.
PHANTOM = ("", "", "", "", 0)


def is_phantom(seg):
    return seg[1] == ""


def make_rect(x, y, w, h):
    return x - w, y - h, x + w, y + h


def rectangles_intersect(l0, t0, r0, b0, l1, t1, r1, b1):
    if l0 > r1 or l1 > r0 or t0 > b1 or t1 > b0:
        return False
    return True


def points_up(a):
    if a == 0:
        return 1
    if a not in POINTS_UP:
        raise ConversionError("unknown arrow code %r" % (a,))
    return POINTS_UP[a]


def is_end(text):
    text = text or ""
    return text.lower() in END_TEXTS or text == "End"


# --------------------------------------------------------------------------
# Stage 1: geometry -> manhattan vertices and edges (graph2.tcl)
# --------------------------------------------------------------------------

class Manhattan:
    """Port of graph2::extract.manhattan for one diagram.

    Lines are tuples (item_id, fixed, low, high, arrow): for a vertical line
    fixed is x and low/high are y1/y2; for a horizontal line fixed is y.
    """

    def __init__(self, items, is_drakon):
        self.items = items
        self.is_drakon = is_drakon
        self.errors = []
        self.hor = {}
        self.ver = {}
        self.icons = {}
        self.next_id = 0
        self.lines = {}
        self.hors = []
        self.vers = []
        self.man_icons = {}
        self.by_center = {}
        self.left, self.right, self.top, self.bottom = {}, {}, {}, {}
        self.begin, self.end = {}, {}

    def report(self, item_id, message):
        self.errors.append((item_id, message))

    def ok(self):
        return not self.errors

    # import (stor.import.*)
    def import_items(self):
        for item in self.items:
            if item["type"] == "commentout":
                continue
            t = item["type"]
            if t == "horizontal":
                self.import_horizontal(item["item_id"], item["x"], item["y"], item["w"], item["a"])
            elif t == "vertical":
                self.import_vertical(item["item_id"], item["x"], item["y"], item["h"], item["a"])
            elif t == "arrow":
                self.import_arrow(item)
            elif t == "parallel":
                self.import_horizontal(item["item_id"], item["x"], item["y"], item["w"], PARALLEL)
            elif t == "if":
                self.import_horizontal(item["item_id"], item["x"] + item["w"], item["y"], item["a"], 0)
                self.icons[item["item_id"]] = item
            else:
                self.icons[item["item_id"]] = item

    def import_horizontal(self, item_id, x, y, w, a):
        self.hor.setdefault(y, []).append((item_id, y, x, x + w, a))

    def import_vertical(self, item_id, x, y, h, a):
        self.ver.setdefault(x, []).append((item_id, x, y, y + h, a))

    def import_arrow(self, item):
        item_id, x, y, w, h, a, b = (item[k] for k in ("item_id", "x", "y", "w", "h", "a", "b"))
        self.import_vertical(item_id, x, y, h, 0)
        y2 = y + h
        if b == 0:
            self.import_horizontal(item_id, x - a, y2, a, 0)
            self.import_horizontal(item_id, x - w, y, w, LEFT_ARROW)
        else:
            self.import_horizontal(item_id, x, y2, a, 0)
            self.import_horizontal(item_id, x, y, w, RIGHT_ARROW)

    # icons.dont.touch
    def icons_dont_touch(self):
        ids = list(self.icons)
        for i in range(len(ids) - 1):
            one = self.icons[ids[i]]
            r1 = make_rect(one["x"], one["y"], one["w"], one["h"])
            for j in range(i + 1, len(ids)):
                other = self.icons[ids[j]]
                r2 = make_rect(other["x"], other["y"], other["w"], other["h"])
                if rectangles_intersect(*r1, *r2):
                    self.report(one["item_id"], "No space between icons.")
        return self.ok()

    # icons.cut.lines
    def icons_cut_lines(self):
        for item in self.icons.values():
            left, top, right, bottom = make_rect(item["x"], item["y"], item["w"], item["h"])
            self._icons_cut(top, bottom, left, right, self.ver)
            self._icons_cut(left, right, top, bottom, self.hor)

    @staticmethod
    def _icons_cut(top, bottom, left, right, lines):
        for x in list(lines):
            if left <= x <= right:
                lines[x] = Manhattan._cut_segments(lines[x], top, bottom)

    @staticmethod
    def _cut_segments(segments, top, bottom):
        out = []
        for seg in segments:
            a = seg[4]
            if a == 0:
                upper, lower = Manhattan._cut_simple(seg, top, bottom, 0, 0)
            elif points_up(a):
                upper, lower = Manhattan._cut_simple(seg, top, bottom, a, 0)
            else:
                upper, lower = Manhattan._cut_simple(seg, top, bottom, 0, a)
            if upper is not None:
                out.append(upper)
            if lower is not None:
                out.append(lower)
        return out

    @staticmethod
    def _cut_simple(seg, top, bottom, ua, la):
        item_id, x, y1, y2 = seg[:4]
        if y1 < top:
            if y2 <= top:
                return seg, None
            upper = (item_id, x, y1, top, ua)
            lower = (item_id, x, bottom, y2, la) if y2 > bottom else None
            return upper, lower
        if y2 > bottom:
            if y1 >= bottom:
                return None, seg
            return None, (item_id, x, bottom, y2, la)
        return None, None

    # merge.lines
    def merge_lines(self):
        for key in list(self.hor):
            self.hor[key] = self._merge_on_line(self.hor[key])
        for key in list(self.ver):
            self.ver[key] = self._merge_on_line(self.ver[key])
        return self.ok()

    def _merge_on_line(self, items):
        if not items:
            return [PHANTOM]
        output = []
        current = None
        for item in sorted(items, key=lambda s: s[2]):
            if current is None:
                current = item
            else:
                to_add, current = self._merge_segments(current, item)
                if to_add is not None:
                    output.append(to_add)
        output.append(current)
        return output

    def _merge_segments(self, current, nxt):
        item_id, x, y1, y2, a = current
        _, _, ny1, ny2, na = nxt
        if ny1 > y2:
            return current, nxt
        if a == 0:
            if na == 0:
                return None, (item_id, x, y1, max(y2, ny2), a)
            if na == PARALLEL:
                self.report(item_id, "This segment takes the same place as another")
                return None, nxt
            return self._line_arrow(current, nxt)
        if a == PARALLEL or na != 0:
            self.report(item_id, "This segment takes the same place as another")
            return None, nxt
        return self._arrow_line(current, nxt)

    @staticmethod
    def _line_arrow(current, nxt):
        item_id, x, y1, y2, a = current
        nid, _, ny1, ny2, na = nxt
        if points_up(na):
            yy = max(y2, ny2)
            to_add = (item_id, x, y1, ny1, a) if ny1 > y1 else None
            return to_add, (nid, x, ny1, yy, na)
        if y2 > ny2:
            return (nid, x, y1, ny2, na), (item_id, x, ny2, y2, 0)
        return None, (nid, x, y1, ny2, na)

    @staticmethod
    def _arrow_line(current, nxt):
        item_id, x, y1, y2, a = current
        nid, _, ny1, ny2, na = nxt
        if points_up(a):
            return None, (item_id, x, y1, max(y2, ny2), a)
        if y2 > ny2:
            return None, current
        return current, (nid, x, y2, ny2, 0)

    # lines.cut.lines
    def lines_cut_lines(self):
        self._lines_cut(self.hor, self.ver)
        self._lines_cut(self.ver, self.hor)

    @staticmethod
    def _lines_cut(cutters, targets):
        for key in list(cutters):
            for cutter in cutters[key]:
                for tkey in list(targets):
                    targets[tkey] = Manhattan._line_cuts_items(cutter, tkey, targets[tkey])

    @staticmethod
    def _line_cuts_items(cutter, y, items):
        if is_phantom(cutter):
            return items
        _, x, y1, y2 = cutter[:4]
        if y < y1 or y > y2:
            return items
        out = []
        for item in items:
            if is_phantom(item):
                continue
            left, right = Manhattan._segment_cut(x, item)
            if left is not None:
                out.append(left)
            if right is not None:
                out.append(right)
        return out

    @staticmethod
    def _segment_cut(x, item):
        item_id, y, x1, x2, a = item
        if x <= x1:
            return None, item
        if x >= x2:
            return item, None
        if points_up(a):
            return (item_id, y, x1, x, a), (item_id, y, x, x2, 0)
        return (item_id, y, x1, x, 0), (item_id, y, x, x2, a)

    # make.man.store
    def new_id(self):
        self.next_id += 1
        return self.next_id

    def make_store(self):
        for key in self.ver:
            for seg in self.ver[key]:
                lid = self.new_id()
                self.lines[lid] = seg
                self.vers.append(lid)
        for key in self.hor:
            for seg in self.hor[key]:
                lid = self.new_id()
                self.lines[lid] = seg
                self.hors.append(lid)
        for item in self.icons.values():
            self.insert_icon(item)

    def insert_icon(self, item):
        iid = self.new_id()
        self.man_icons[iid] = item
        self.by_center["%s,%s" % (item["x"], item["y"])] = iid
        return iid

    def get_knot(self, x, y):
        key = "%s,%s" % (x, y)
        if key in self.by_center:
            return self.by_center[key]
        return self.insert_icon({"item_id": "", "type": "knot", "text": "", "text2": "",
                                 "x": x, "y": y, "w": 0, "h": 0, "a": 0, "b": 0})

    def set_side(self, side, icon_id, line_id):
        getattr(self, side)[icon_id] = line_id
        if side in ("bottom", "right"):
            self.begin[line_id] = icon_id
        else:
            self.end[line_id] = icon_id

    def complain_two_attached(self, line_id):
        self.report(self.lines[line_id][0], "This icon has several lines on its side.")

    # attach.to.icons
    def attach_to_icons(self):
        for iid in list(self.man_icons):
            item = self.man_icons[iid]
            left, top, right, bottom = make_rect(item["x"], item["y"], item["w"], item["h"])
            for lid in self.vers:
                if is_phantom(self.lines[lid]):
                    continue
                _, x, y1, y2, _ = self.lines[lid]
                if x < left or x > right:
                    continue
                if y2 == top:
                    if lid not in self.end:
                        self.set_side("top", iid, lid)
                    else:
                        self.complain_two_attached(lid)
                elif y1 == bottom:
                    if lid not in self.begin:
                        self.set_side("bottom", iid, lid)
                    else:
                        self.complain_two_attached(lid)
            for lid in self.hors:
                if is_phantom(self.lines[lid]):
                    continue
                _, y, x1, x2, _ = self.lines[lid]
                if y < top or y > bottom:
                    continue
                if x2 == left:
                    if lid not in self.end:
                        self.set_side("left", iid, lid)
                    else:
                        self.complain_two_attached(lid)
                elif x1 == right:
                    if lid not in self.begin:
                        self.set_side("right", iid, lid)
                    else:
                        self.complain_two_attached(lid)
        return self.ok()

    # insert.knots
    def insert_knots(self):
        for lid in self.vers:
            _, x, y1, y2, _ = self.lines[lid]
            if lid not in self.begin:
                self.set_side("bottom", self.get_knot(x, y1), lid)
            if lid not in self.end:
                self.set_side("top", self.get_knot(x, y2), lid)
        for lid in self.hors:
            _, y, x1, x2, _ = self.lines[lid]
            if lid not in self.begin:
                self.set_side("right", self.get_knot(x1, y), lid)
            if lid not in self.end:
                self.set_side("left", self.get_knot(x2, y), lid)

    def sides(self, iid):
        return self.left.get(iid), self.top.get(iid), self.right.get(iid), self.bottom.get(iid)

    # check.dangling
    def check_dangling(self):
        for iid, item in self.man_icons.items():
            if item["type"] != "knot":
                continue
            present = [s for s in self.sides(iid) if s is not None]
            if len(present) == 1:
                self.report(self.lines[present[0]][0], "Line not connected to any icon.")
        return self.ok()

    # check.on.one.line
    def check_on_one_line(self):
        for iid in self.man_icons:
            left, top, right, bottom = self.sides(iid)
            self._check_on_line(left, right, False)
            self._check_on_line(top, bottom, True)
        return self.ok()

    def _check_on_line(self, first, second, is_vertical):
        if first is None or second is None:
            return
        if self.lines[first][1] != self.lines[second][1]:
            message = "Broken vertical line." if is_vertical else "Broken horizontal line."
            self.report(self.lines[first][0], message)

    # connected.check
    def connected_check(self):
        start = -1
        for iid, item in self.man_icons.items():
            if item["type"] != "commentin" or any(s is not None for s in self.sides(iid)):
                start = iid
                break
        marked = set()
        stack = [start]
        while stack:
            iid = stack.pop()
            if iid in marked:
                continue
            marked.add(iid)
            left, top, right, bottom = self.sides(iid)
            if left is not None:
                stack.append(self.begin.get(left))
            if right is not None:
                stack.append(self.end.get(right))
            if top is not None:
                stack.append(self.begin.get(top))
            if bottom is not None:
                stack.append(self.end.get(bottom))
        for iid, item in self.man_icons.items():
            if iid not in marked and item["type"] != "commentin":
                self.report("", "All icons must be connected together.")
                return False
        return True

    def run(self):
        """extract.manhattan. Returns (vertices, edges) or None on errors."""
        self.import_items()
        if not self.icons_dont_touch():
            return None
        self.icons_cut_lines()
        if not self.merge_lines():
            return None
        self.lines_cut_lines()
        self.make_store()
        if not self.attach_to_icons():
            return None
        self.insert_knots()
        if not self.check_dangling():
            return None
        if not self.check_on_one_line():
            return None
        if self.is_drakon and not self.connected_check():
            return None
        return self.export()

    # export.result
    def export(self):
        edges = {}
        for lid in self.vers + self.hors:
            seg = self.lines[lid]
            edges[lid] = {
                "v1": self.begin.get(lid), "v2": self.end.get(lid),
                "head": ARROW_NAMES[seg[4]] if seg[4] else "",
                "vertical": lid in self.vers, "items": seg[0],
            }
        vertices = {}
        for iid, item in self.man_icons.items():
            left, top, right, bottom = self.sides(iid)
            vtype, text = item["type"], item.get("text") or ""
            if vtype == "commentin":
                if left is None and top is None and right is None and bottom is None:
                    continue
                vtype, text = "action", ""
                item["type"], item["text"] = "action", ""
            elif vtype == "knot":
                vtype = ""
            vertices[iid] = {
                "item_id": item["item_id"], "type": vtype, "text": text,
                "x": item["x"], "y": item["y"],
                "up": top, "left": left, "right": right, "down": bottom,
                "marked": False, "parent": 0,
            }
        return vertices, edges


# --------------------------------------------------------------------------
# Stage 2: vertices and edges -> logical links (auto.tcl)
# --------------------------------------------------------------------------

class Auto:
    """Port of graph::p.do_extract_auto for one diagram."""

    def __init__(self, name, vertices, edges, items_by_id, errors):
        self.name = name
        self.v = vertices
        self.e = edges
        self.items_by_id = items_by_id
        self.errors = errors
        self.links = {}  # src -> list of [ordinal, dst, direction], in insertion order
        self.branches = []  # dicts: ordinal, header, start, params, first
        self.loop_pairs = {}
        self.via = {}  # (src, ordinal) -> first knot of a link shortened by skip_joints

    # errors
    def error(self, items, message):
        key = (str(items), message)
        if key not in self.errors:
            self.errors.append(key)

    def has_errors(self):
        return bool(self.errors)

    def edge_items(self, edge_id):
        return self.e[edge_id]["items"] if edge_id is not None else ""

    def unexpected_edge(self, edge_id):
        if edge_id is None or edge_id not in self.e:
            return
        self.error(self.e[edge_id]["items"], "Line not expected here.")

    def unexpected_vertex(self, vid):
        if vid not in self.v:
            return
        vtype = self.v[vid]["type"]
        if vtype in ("timer", "pause"):
            message = "Elements of type '%s' are not supported by the verifier yet." % vtype
        else:
            message = "Icon '%s' not expected here." % vtype
        self.error(self.v[vid]["item_id"], message)

    # graph helpers
    def info(self, vid):
        """p.get_info: (type, text, up, left, right, down) with neighbour vertex ids."""
        v = self.v[vid]
        up = self.e[v["up"]]["v1"] if v["up"] is not None else None
        left = self.e[v["left"]]["v1"] if v["left"] is not None else None
        right = self.e[v["right"]]["v2"] if v["right"] is not None else None
        down = self.e[v["down"]]["v2"] if v["down"] is not None else None
        return v["type"], v["text"], up, left, right, down

    def require(self, vid):
        if vid is None or vid not in self.v:
            raise ConversionError('expected boolean value but got ""')
        return self.v[vid]

    def is_marked(self, vid):
        return self.require(vid)["marked"]

    def mark(self, vid):
        if vid in self.v:
            self.v[vid]["marked"] = True

    def check_and_mark(self, vid):
        v = self.require(vid)
        if v["marked"]:
            return False
        v["marked"] = True
        return True

    def link(self, src, ordinal, dst, direction):
        if src is None:
            raise ConversionError("p.link: from is empty")
        for entry in self.links.setdefault(src, []):
            if entry[0] == ordinal:
                if entry[1] != dst:
                    raise ConversionError("Link not unique: %s, %s -> old: %s new: %s." % (src, ordinal, entry[1], dst))
                return
        self.links[src].append([ordinal, dst, direction])

    def get_link(self, src, ordinal):
        for entry in self.links.get(src, []):
            if entry[0] == ordinal:
                return entry[1]
        return None

    def first_link(self, src):
        entries = self.links.get(src, [])
        return entries[0][1] if entries else None

    def unlink(self, src):
        self.links.pop(src, None)

    def unlink_one(self, src, ordinal):
        self.links[src] = [e for e in self.links.get(src, []) if e[0] != ordinal]

    def relink(self, src, old, new, direction):
        for entry in self.links.get(src, []):
            if entry[0] == old:
                entry[0], entry[2] = new, direction
                return
        raise ConversionError("Link not found: %s %s" % (src, old))

    def is_cross(self, vid):
        v = self.v[vid]
        if v["up"] is not None and v["left"] is not None and v["right"] is not None and v["down"] is not None:
            self.error(self.edge_items(v["left"]), "Line crossings are not allowed.")
            return True
        return False

    def find_rightmost(self, vid):
        current = vid
        while self.v[current]["right"] is not None:
            current = self.e[self.v[current]["right"]]["v2"]
        return current

    def check_right_goes_up(self, vid):
        rightmost = self.find_rightmost(vid)
        if self.v[rightmost]["down"] is not None:
            self.error(self.edge_items(self.v[rightmost]["left"]), "The line should go up at the right.")
            return False
        return True

    def get_params(self, start):
        edge = self.v[start]["right"] if start in self.v else None
        return self.e[edge]["v2"] if edge is not None else None

    # traversal (s.*)
    def s_down(self, src, vid, is_primitive, is_skewer, depth):
        self.link(src, 1, vid, "down")
        if not self.check_and_mark(vid):
            return
        vtype, text, up, left, right, down = self.info(vid)
        if vtype in ("action", "shelf"):
            self.s_down(vid, down, is_primitive, is_skewer, depth)
        elif vtype == "if":
            self.s_down(vid, down, is_primitive, is_skewer, depth)
            self.s_right(vid, right, is_primitive, True, 2)
        elif vtype == "loopstart":
            self.s_down(vid, down, is_primitive, is_skewer, depth + 1)
        elif vtype == "loopend":
            if depth == 0:
                self.unexpected_vertex(vid)
                return
            self.s_down(vid, down, is_primitive, is_skewer, depth - 1)
        elif vtype == "select":
            self.s_select_joint(vid, down, is_primitive, is_skewer, depth)
        elif vtype == "address":
            if is_primitive or depth != 0:
                self.unexpected_vertex(vid)
                return
            self.p_address(vid)
        elif vtype == "beginend":
            if not is_end(text) or depth != 0:
                self.unexpected_vertex(vid)
        elif vtype == "":
            if self.is_cross(vid):
                return
            if is_skewer or depth != 0:
                if left is not None:
                    self.unexpected_edge(self.v[vid]["left"])
                    return
                if down is None:
                    self.unexpected_edge(self.v[vid]["right"])
                    return
            if down is not None:
                right_edge = self.v[vid]["right"]
                if right_edge is not None and self.e[right_edge]["head"] != "left arrow":
                    self.check_right_goes_up(vid)
                self.s_down(vid, down, is_primitive, is_skewer, depth)
            elif left is not None:
                self.s_left(vid, left, is_primitive)
            elif right is not None:
                self.s_right(vid, right, is_primitive, False, 1)
        else:
            self.unexpected_vertex(vid)

    def s_select_joint(self, select, vid, is_primitive, is_skewer, depth):
        if vid is None:
            raise ConversionError("select without a line below")
        if self.is_cross(vid):
            return
        vtype, _, up, left, right, down = self.info(vid)
        if vtype != "":
            self.unexpected_vertex(vid)
            return
        item_id = self.v[select]["item_id"]
        if left is not None or right is None or down is None:
            self.error(item_id, "A right t-joint expected after the 'select' icon.")
            return
        self.s_case(1, select, down, is_primitive, is_skewer, depth)
        current, i = right, 2
        while current is not None:
            vtype, _, up, left, right, down = self.info(current)
            if vtype != "":
                self.unexpected_vertex(current)
                return
            if self.is_cross(current):
                return
            if up is not None or down is None:
                self.error(item_id, "Expected a line with a 'case' icon.")
                return
            self.s_case(i, select, down, is_primitive, False, 0)
            i += 1
            current = right

    def s_case(self, ordinal, select, vid, is_primitive, is_skewer, depth):
        self.link(select, ordinal, vid, "down" if ordinal == 1 else "step")
        vtype, _, up, left, right, down = self.info(vid)
        if vtype == "":
            self.error(self.edge_items(self.v[vid]["up"]), "A 'case' icon expected.")
            return
        if vtype != "case":
            self.unexpected_vertex(vid)
            return
        self.s_down(vid, down, is_primitive, is_skewer, depth)

    def s_left(self, src, vid, is_primitive):
        self.link(src, 1, vid, "left")
        if self.is_marked(vid):
            return
        if self.is_cross(vid):
            return
        vtype, _, up, left, right, down = self.info(vid)
        if vtype != "":
            self.unexpected_vertex(vid)
            return
        if left is not None and down is not None and up is None:
            self.unexpected_edge(self.v[vid]["down"])
            return
        if left is None:
            if up is None or down is None:
                self.error(self.edge_items(self.v[vid]["right"]), "Wrong turn.")
                return
        else:
            self.mark(vid)
            self.s_left(vid, left, is_primitive)

    def s_up(self, src, vid, is_primitive):
        self.link(src, 1, vid, "up")
        if self.is_cross(vid):
            return
        if not self.check_and_mark(vid):
            return
        vtype, _, up, left, right, down = self.info(vid)
        if vtype != "":
            self.unexpected_vertex(vid)
            return
        if left is None or up is not None or right is not None:
            self.error(self.edge_items(self.v[vid]["down"]), "The line should turn left at the top.")
            return
        self.s_arrow(vid, left)

    def s_arrow(self, src, vid):
        if self.is_cross(vid):
            return
        self.link(src, 1, vid, "arrow")
        vtype, _, up, left, right, down = self.info(vid)
        if vtype != "":
            self.unexpected_vertex(vid)
            return
        redge = self.v[vid]["right"]
        items = self.edge_items(redge)
        head = self.e[redge]["head"] if redge is not None else ""
        if head != "left arrow":
            self.error(items, "Arrow expected.")
            return
        if left is not None or up is None or down is None:
            self.error(items, "Arrow points to a wrong place.")

    def s_right(self, src, vid, is_primitive, down_allowed, ordinal):
        self.link(src, ordinal, vid, "right")
        if vid is None:
            raise ConversionError('expected boolean value but got ""')
        if self.is_cross(vid):
            return
        if self.is_marked(vid):
            return
        vtype, _, up, left, right, down = self.info(vid)
        if right is not None and down is not None:
            self.unexpected_edge(self.v[vid]["down"])
            return
        if right is not None and up is not None:
            self.unexpected_edge(self.v[vid]["up"])
            return
        if right is None:
            if up is not None and down is not None:
                return
            self.mark(vid)
            if down is not None:
                if not down_allowed:
                    self.unexpected_edge(self.v[vid]["down"])
                    return
                self.s_down(vid, down, is_primitive, False, 0)
            else:
                self.s_up(vid, up, is_primitive)
        else:
            self.mark(vid)
            self.s_right(vid, right, is_primitive, down_allowed, 1)

    # addresses (p.address and checks)
    def p_address(self, vid):
        downe = self.v[vid]["down"]
        if downe is None:
            raise ConversionError("address without a line below")
        down_vertex, items = self.e[downe]["v2"], self.e[downe]["items"]
        self.check_bottom_right_ok(down_vertex, items)
        self.check_bottom_arrow_ok(down_vertex)

    def check_bottom_right_ok(self, vid, items):
        current = vid
        while current is not None:
            vtype, _, up, left, right, down = self.info(current)
            if vtype != "":
                self.unexpected_vertex(current)
                return
            if left is None:
                self.error(items, "A left-leading line expected here.")
                return
            if down is not None:
                self.unexpected_edge(self.v[current]["down"])
                return
            current = right

    def check_bottom_arrow_ok(self, down_vertex):
        current = down_vertex
        while current is not None:
            vtype, _, up, left, right, down = self.info(current)
            if vtype != "":
                self.unexpected_vertex(current)
                return
            items = self.edge_items(self.v[current]["right"])
            if up is None or down is not None:
                self.error(items, "Error near this line.")
                return
            if left is None:
                utype, _, uup, uleft, _, _ = self.info(up)
                if utype != "":
                    self.unexpected_vertex(up)
                    return
                if uleft is not None:
                    self.unexpected_edge(self.v[up]["left"])
                    return
                if uup is not None:
                    self.unexpected_edge(self.v[up]["up"])
                    return
                arrow_edge = self.v[up]["right"]
                if arrow_edge is not None and self.e[arrow_edge]["head"] != "right arrow":
                    self.error(self.e[arrow_edge]["items"], "Arrow expected here.")
                return
            current = left

    # starts and branches
    def find_starts(self):
        ends = 0
        starts = []
        candidates = sorted((v["x"], vid) for vid, v in self.v.items() if v["type"] == "beginend")
        for _, vid in candidates:
            v = self.v[vid]
            if v["left"] is not None:
                self.unexpected_edge(v["left"])
            elif v["down"] is None and v["right"] is not None:
                self.unexpected_edge(v["right"])
            elif v["down"] is not None and v["up"] is not None:
                self.unexpected_edge(v["up"])
            elif v["down"] is None and v["up"] is None:
                self.error(v["item_id"], "Disconnected icon.")
            if v["down"] is None:
                if is_end(v["text"]):
                    ends += 1
                else:
                    self.error(v["item_id"], "'End' icon should have the text 'End'")
            else:
                starts.append(vid)
        if ends != 1:
            self.error("", "The diagram must have exactly one end.")
        if not starts:
            self.error("", "The diagram must have one or more starts.")
        return starts

    def headers_by_x(self):
        # FIX: left to right. The original uses Tcl hash order here.
        return [vid for _, _, vid in sorted((v["x"], v["y"], vid) for vid, v in self.v.items() if v["type"] == "branch")]

    def create_branches(self):
        headers = self.headers_by_x()
        footers = [vid for vid, v in self.v.items() if v["type"] == "address"]
        if headers and not footers:
            self.error("", "Missing one or more address icons.")
            return
        names = {}
        for header in headers:
            text = (self.v[header]["text"] or "").strip()
            if not text:
                self.error(self.v[header]["item_id"], "No text in the branch header.")
                return
            if text in names:
                self.error(self.v[header]["item_id"], "Branch name %s is not unique." % text)
                return
            names[text] = header
        for footer in footers:
            text = (self.v[footer]["text"] or "").strip()
            if not text:
                self.error(self.v[footer]["item_id"], "No text in the address header.")
                return
            if text not in names:
                self.error(self.v[footer]["item_id"], "Branch name %s is not found." % text)
                return
            self.link(footer, 1, names[text], "branch")
        if not headers:
            self.branches.append({"ordinal": 1, "header": None, "start": None, "params": None, "first": None})
        else:
            for i, header in enumerate(headers):
                self.branches.append({"ordinal": i + 1, "header": header, "start": None, "params": None, "first": None})

    def branch(self, ordinal):
        for b in self.branches:
            if b["ordinal"] == ordinal:
                return b
        return None

    def is_machine(self):
        name = (self.name or "").lower()
        if name == "state machine" or name.startswith("sm "):
            return True
        starts = self.find_starts()
        if not starts:
            return False
        params = self.get_params(starts[0])
        if params is None:
            return False
        return (self.v[params]["text"] or "").strip().startswith("state machine")

    def is_reachable(self, vid):
        return any(e[1] == vid for entries in self.links.values() for e in entries)

    def check_reachable(self):
        headers = [b["header"] for b in self.branches]
        machine = self.is_machine()
        last = len(headers) - 1
        for i in range(1, len(headers)):
            if machine and i == last:
                continue
            if not self.is_reachable(headers[i]):
                self.error(self.v[headers[i]]["item_id"], "This branch is unreachable.")

    def degrade_silhouette_check(self, starts):
        if len(self.branches) < len(starts):
            self.error("", "Too many 'begin' icons.")
            return
        if len(self.branches) == 1 and any(v["type"] == "branch" for v in self.v.values()):
            self.error("", "A silouette must have more than one branch.")

    def check_parameters(self, begin):
        edge = self.v[begin]["right"]
        if edge is None:
            return None
        pv = self.e[edge]["v2"]
        v = self.v[pv]
        if v["up"] is not None or v["right"] is not None or v["down"] is not None:
            self.error(v["item_id"], "Unexpected lines around the parameters icon.")
        if v["type"] != "action":
            self.error(v["item_id"], "Only action icon can serve as a parameters icon.")
        return pv

    def check_icons_on_verticals(self, starts):
        params = [p for p in (self.check_parameters(s) for s in starts) if p is not None]
        kinds = ("action", "if", "branch", "case", "insertion", "loopend", "loopstart", "select", "address")
        for vid, v in self.v.items():
            if v["type"] not in kinds or vid in params:
                continue
            if v["left"] is not None:
                self.unexpected_edge(v["left"])
            if v["type"] != "if" and v["right"] is not None:
                self.unexpected_edge(v["right"])
            if v["up"] is None or v["down"] is None:
                self.error(v["item_id"], "This icon should be placed on a vertical line.")

    # trace
    def connect_branch_to_start(self, ordinal, start):
        b = self.branch(ordinal)
        b["start"], b["params"] = start, self.get_params(start)

    def trace(self, starts):
        for v in self.v.values():
            v["marked"] = False
        first = starts[0]
        if len(self.branches) == 1:
            _, _, _, _, _, down = self.info(first)
            self.connect_branch_to_start(1, first)
            self.branch(1)["first"] = down
            self.s_down(first, down, True, True, 0)
        else:
            count = sum(1 for e in self.e.values() if not e["vertical"] and e["head"] == "right arrow")
            if count != 1:
                self.error("", "A silouette must have exactly one arrow at the right side.")
                return
            for b in self.branches:
                header = b["header"]
                self.try_connect_branch_to_start(b["ordinal"], header)
                _, _, _, _, _, down = self.info(header)
                b["first"] = down
                self.s_down(header, down, False, True, 0)

    def try_connect_branch_to_start(self, ordinal, header):
        _, _, up, _, _, _ = self.info(header)
        if up is None:
            self.error(self.v[header]["item_id"], "A going up line expected here.")
            return
        _, _, nup, _, _, _ = self.info(up)
        self.trace_to_arrow(up)
        if nup is None:
            return
        if self.v[nup]["type"] == "beginend":
            self.connect_branch_to_start(ordinal, nup)

    def trace_to_arrow(self, header_node):
        current = header_node
        while True:
            vtype, _, up, left, right, down = self.info(current)
            if vtype != "":
                self.unexpected_vertex(current)
                return
            if left is None:
                self.error("", "Arrow expected at the top of the diagram.")
                return
            edge = self.e[self.v[current]["left"]]
            if edge["head"] == "left arrow":
                self.error(edge["items"], "Left arrow not expected.")
                return
            if edge["head"] == "right arrow":
                break
            current = left
        current = header_node
        while current is not None:
            vtype, _, up, left, right, down = self.info(current)
            if vtype != "":
                self.unexpected_vertex(current)
                return
            if up is not None:
                uv = self.v[up]
                if uv["type"] == "":
                    self.unexpected_edge(uv["down"])
                    return
                if uv["type"] != "beginend" or down is None:
                    self.unexpected_vertex(up)
                    return
            if down is not None:
                dv = self.v[down]
                if dv["type"] == "":
                    self.unexpected_edge(dv["up"])
                    return
                if dv["type"] != "branch":
                    self.unexpected_vertex(down)
            current = right

    # loops
    def below(self, vid):
        edge = self.v[vid]["down"]
        return self.e[edge]["v2"] if edge is not None else None

    def loops(self):
        for v in self.v.values():
            v["parent"], v["marked"] = 0, False
        if len(self.branches) == 1:
            self.scan_loops(self.branches[0]["start"], 0)
        else:
            for b in self.branches:
                self.scan_loops(b["header"], 0)

    def scan_loops(self, vid, parent):
        current = vid
        while current is not None:
            if not self.check_and_mark(current):
                return None
            below = self.below(current)
            self.v[current]["parent"] = parent
            vtype, text = self.v[current]["type"], self.v[current]["text"]
            if vtype == "loopstart":
                result = self.scan_loops(below, current)
                last, after_loop = result if result else (None, None)
                self.relink(current, 1, 2, "step")
                if last is not None:
                    self.unlink(last)
                    self.loop_pairs[last] = current
                self.link(current, 1, after_loop, "down")
                below = after_loop
            elif vtype == "loopend":
                return current, self.first_link(current)
            elif vtype == "if":
                if_start = self.get_if_start(current)
                if if_start is not None:
                    self.scan_loops(if_start, parent)
            elif vtype == "select":
                for entry in list(self.links.get(current, [])):
                    if entry[0] > 1:
                        self.scan_loops(entry[1], parent)
            elif vtype == "beginend":
                if is_end(text):
                    return None
            elif vtype == "address":
                return None
            current = below
        return None

    def get_if_start(self, vid):
        current = vid
        while True:
            _, _, up, _, right, _ = self.info(current)
            if right is None:
                return None if up is not None else current
            current = right

    def parent(self, vid):
        return self.v[vid]["parent"] if vid in self.v else None

    def is_vertical_tjoint(self, vid):
        if vid not in self.v:
            raise ConversionError("Vertex %s not found" % vid)
        v = self.v[vid]
        if v["up"] is None or v["down"] is None:
            return False
        return v["left"] is not None or v["right"] is not None

    def is_same_or_parent(self, vid, parent):
        if parent == 0:
            return True
        current = vid
        seen = set()
        while current != 0 and current is not None and current not in seen:
            if current == parent:
                return True
            seen.add(current)
            current = self.parent(current)
        return False

    def check_loops(self):
        memo = set()
        for b in self.branches:
            self.check_loop_entries(b["first"], 0, memo)

    def check_loop_entries(self, vid, src_parent, memo):
        # FIX: memoised; same result as the original, without exponential time.
        if (vid, src_parent) in memo:
            return
        memo.add((vid, src_parent))
        for ordinal, dst, direction in list(self.links.get(vid, [])):
            if direction == "branch":
                continue
            dst_parent = self.parent(dst)
            if direction == "arrow" or (direction == "left" and self.is_vertical_tjoint(dst)):
                if not self.is_same_or_parent(src_parent, dst_parent):
                    self.unexpected_edge(self.v[dst]["right"])
                    return
            else:
                vtype = self.v[vid]["type"]
                if vtype == "loopstart" and ordinal == 2:
                    parent = dst
                elif vtype in ("if", "select") and ordinal > 1:
                    parent = self.parent(vid)
                else:
                    parent = src_parent
                self.check_loop_entries(dst, parent, memo)

    def check_infinite(self):
        if self.is_machine():
            return
        headers = self.headers_by_x()
        if len(headers) == 1:
            return
        for v in self.v.values():
            v["marked"] = False
        exits = {h: self.find_exits(h) for h in headers}
        if len(headers) > 1:
            last = next((h for h in headers if not exits[h]), None)
            if last is None:
                raise ConversionError("Last branch not found")
            for header in headers:
                if not self.can_reach(header, last, exits):
                    self.error(self.v[header]["item_id"], "An infinite loop detected.")

    def find_exits(self, vid):
        if not self.check_and_mark(vid):
            return []
        result = []
        for _, dst, direction in list(self.links.get(vid, [])):
            if direction == "branch":
                result.append(dst)
            else:
                result.extend(self.find_exits(dst))
        return result

    @staticmethod
    def can_reach(start, target, graph):
        seen, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(graph.get(node, []))
        return False

    def check_cases(self):
        for vid, v in self.v.items():
            if v["type"] != "select":
                continue
            entries = sorted(self.links.get(vid, []), key=lambda e: e[0])
            texts = [self.v[e[1]]["text"] if e[1] in self.v else "" for e in entries]
            seen = []
            last = len(texts) - 1
            for i, text in enumerate(texts):
                dst = self.get_link(vid, i + 1)
                items = self.v[dst]["item_id"] if dst in self.v else ""
                if i == 0 and text == "":
                    self.error(items, "First case icon cannot be empty.")
                elif i == 0 and text.lower() == "else":
                    self.error(items, "First case icon cannot be Else.")
                elif i != last and text == "":
                    self.error(items, "The empty case icon should be the last one.")
                elif i != last and text.lower() == "else":
                    self.error(items, "The Else case icon should be the last one.")
                if text != "":
                    if text in seen:
                        self.error(items, "%s is not a unique case branch." % text)
                    seen.append(text)

    # skip_joints
    def first_non_joint(self, vid):
        current, steps = vid, 0
        while current is None or self.v[current]["type"] == "":
            current = self.first_link(current)
            steps += 1
            if current is None or steps > len(self.v):
                raise ConversionError("joint chain without an icon")
        return current

    def skip_joints(self):
        for v in self.v.values():
            v["marked"] = False
        if len(self.branches) == 1:
            self.skip_joints_from(self.branches[0]["start"])
        else:
            for b in self.branches:
                self.skip_joints_from(b["header"])

    def skip_joints_from(self, vid):
        if not self.check_and_mark(vid):
            return
        count = len(self.links.get(vid, []))
        for i in range(count):
            ordinal = i + 1
            dst = self.get_link(vid, ordinal)
            vtype = self.v[dst]["type"] if dst in self.v else ""
            if vtype == "":
                icon = self.first_non_joint(dst)
                self.unlink_one(vid, ordinal)
                self.link(vid, ordinal, icon, "short")
                self.via[(vid, ordinal)] = dst
                self.skip_joints_from(icon)
            else:
                self.skip_joints_from(dst)

    def run(self):
        """p.do_extract_auto. Returns True when the diagram is valid."""
        for v in self.v.values():
            item = self.items_by_id.get(v["item_id"])
            if item is not None:
                v["type"], v["text"] = item["type"], item.get("text") or ""
        starts = self.find_starts()
        if self.has_errors():
            return False
        self.create_branches()
        if self.has_errors():
            return False
        self.check_reachable()
        if self.has_errors():
            return False
        self.degrade_silhouette_check(starts)
        if self.has_errors():
            return False
        self.check_icons_on_verticals(starts)
        if self.has_errors():
            return False
        self.trace(starts)
        if self.has_errors():
            return False
        self.loops()
        self.check_loops()
        if self.has_errors():
            return False
        self.check_infinite()
        if self.has_errors():
            return False
        self.check_cases()
        if self.has_errors():
            return False
        self.skip_joints()
        return True


# --------------------------------------------------------------------------
# Stage 3: logical graph -> DrakonTech / DrakonWidget JSON (drakon_tech.tcl)
# --------------------------------------------------------------------------

def strip_foreach(text):
    return text[len("foreach "):] if text.startswith("foreach ") else text


KEPT_TYPES = ("insertion", "input", "output", "process")


def to_widget(auto, items_by_id, originals=None):
    """Port of gen_drakon_tech::convert_diagram.

    originals maps item_id to the item as stored in the .drn. When given,
    original icon types and text2 are kept (see the module docstring).
    """
    v = auto.v
    # rewire_selects_for_tech: case N gets "two" -> case N+1
    for vid, vert in v.items():
        if vert["type"] != "select":
            continue
        entries = sorted(auto.links.get(vid, []), key=lambda e: e[0])
        prev = None
        for ordinal, below, _ in entries:
            if ordinal > 1:
                auto.links.setdefault(prev, []).append([2, below, None])
                auto.unlink_one(vid, ordinal)
            prev = below

    diagram = {"type": "drakon"}
    for b in auto.branches:
        if b["params"] is not None:
            diagram["params"] = items_by_id[v[b["params"]]["item_id"]].get("text") or ""

    # FIX: the actual start icon, whichever branch it sits above.
    starts = {b["start"] for b in auto.branches if b["start"] is not None}
    ordinal_of_header = {b["header"]: b["ordinal"] for b in auto.branches if b["header"] is not None}

    # find_after_arrow: the knots where an arrow loop re-enters the line.
    entries = []
    for vid in v:
        for _, dst, direction in auto.links.get(vid, []):
            if direction == "arrow" and dst not in entries:
                entries.append(dst)
    entry_set = set(entries)

    def chain(start, redirect):
        """Follow knots from start: ("arrow", entry knot) or ("icon", vertex)."""
        current, steps = start, 0
        while current is not None and v[current]["type"] == "":
            if current in entry_set:
                return ("arrow", current)
            current = auto.first_link(current)
            steps += 1
            if steps > len(v):
                raise ConversionError("joint chain without an icon")
        if current is None:
            return None
        if redirect and current in innermost:
            # Like the original: a link that reaches the icon below an arrow
            # loop without passing the arrow knot still goes to the arrow item.
            return ("arrow", innermost[current])
        return ("icon", current)

    innermost = {}
    for entry in entries:
        target = chain(auto.first_link(entry), False)
        if target is not None and target[0] == "icon":
            innermost[target[1]] = entry

    def link_target(vid, ordinal):
        if vid not in v or auto.get_link(vid, ordinal) is None:
            return None
        start = auto.via.get((vid, ordinal), auto.get_link(vid, ordinal))
        return chain(start, True)

    items = {}
    has_branch = False
    max_id = 0
    for vid, vert in v.items():
        vtype = vert["type"]
        if vtype == "branch":
            has_branch = True
        elif vtype == "address":
            continue
        if vtype == "" or vid in starts:
            continue
        item_id = vert["item_id"]
        max_id = max(max_id, int(item_id))
        one, two = link_target(vid, 1), link_target(vid, 2)
        item = {"type": vtype, "content": vert["text"]}
        if vtype == "if":
            item["type"] = "question"
            item["flag1"] = 1 if items_by_id[item_id].get("b") == 1 else 0
            item["one"], item["two"] = one, two
        elif vtype == "loopstart":
            item["type"] = "loopbegin"
            item["one"] = two
            item["content"] = strip_foreach(vert["text"])
        elif vtype == "loopend":
            item["one"] = link_target(vert["parent"], 1)
        elif vtype == "branch":
            # FIX: the branch's own ordinal (original: lookup via the icon below).
            item["branchId"] = ordinal_of_header[vid]
            item["one"] = one
        else:
            if vtype == "beginend":
                item["type"] = "end"
            if one is not None:
                item["one"] = one
            if two is not None:
                item["two"] = two
            if vtype == "action" and one is None:
                continue  # the parameters icon, or an unconnected action
        if originals is not None:
            original = originals.get(item_id, {})
            if vtype == "action" and original.get("type") in KEPT_TYPES:
                item["type"] = original["type"]
            if original.get("text2"):
                item["secondary"] = original["text2"]
        items[str(item_id)] = item

    if not has_branch:
        max_id += 1
        first = auto.branches[0]["first"]
        items[str(max_id)] = {"type": "branch", "branchId": 0,
                              "one": chain(first, True) if first is not None else None}

    # insert_arrow_loops
    arrow_ids = {}
    for entry in entries:
        max_id += 1
        arrow_ids[entry] = str(max_id)
        items[str(max_id)] = {"type": "arrow-loop", "one": chain(auto.first_link(entry), False)}

    def to_id(target):
        if target is None:
            return ""
        kind, vid = target
        if kind == "arrow":
            return arrow_ids[vid]
        if v[vid]["type"] == "address":
            # An address stands for the branch it names.
            header = auto.get_link(vid, 1)
            return str(v[header]["item_id"]) if header is not None else ""
        return str(v[vid]["item_id"])

    for item in items.values():
        for field in ("one", "two"):
            if field in item:
                item[field] = to_id(item[field])

    diagram["items"] = items
    return diagram


# --------------------------------------------------------------------------
# Reading .drn files
# --------------------------------------------------------------------------

def _columns(db, table):
    return {row[1] for row in db.execute("pragma table_info(%s)" % table)}


def read_drn(path):
    """Yield (diagram_id, name, is_drakon, items) for every diagram."""
    db = sqlite3.connect("file:%s?mode=ro" % pathname2url(os.path.abspath(path)), uri=True)
    try:
        have = _columns(db, "items")
        select = ", ".join(c if c in have else "NULL" for c in ITEM_COLUMNS)
        tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
        types = {}
        if "tree_nodes" in tables:
            types = dict(db.execute("select diagram_id, type from tree_nodes where diagram_id is not null"))
        for diagram_id, name in db.execute("select diagram_id, name from diagrams order by diagram_id").fetchall():
            rows = db.execute("select %s from items where diagram_id = ? order by item_id" % select, (diagram_id,)).fetchall()
            items = []
            for row in rows:
                item = dict(zip(ITEM_COLUMNS, row))
                for k in ("x", "y", "w", "h", "a", "b"):
                    item[k] = item[k] if item[k] is not None else 0
                item["text"] = item["text"] if item["text"] is not None else ""
                items.append(item)
            dtype = types.get(diagram_id, "")
            yield diagram_id, name, dtype in ("", "item", None), items
    finally:
        db.close()


def convert_diagram(name, is_drakon, items, official=False):
    """Convert one diagram. Returns a dict with errors and, if valid, "drakon".

    official=True reproduces the DrakonTech exporter exactly (see the module
    docstring); the default keeps original icon types and text2.
    """
    result = {"name": name, "is_drakon": is_drakon, "errors": []}
    errors = []
    # graph::copy_from: these types are verified as plain actions.
    work = []
    for item in items:
        item = dict(item)
        if item["type"] == "parallel":
            errors.append((str(item["item_id"]), "Elements of type 'parallel' are not supported by the verifier yet."))
        if item["type"] in ("insertion", "input", "output", "process"):
            item["type"] = "action"
        work.append(item)
    try:
        man = Manhattan(work, is_drakon)
        graph = man.run()
        for item_id, message in man.errors:
            key = (str(item_id), message)
            if key not in errors:
                errors.append(key)
        if graph is not None and is_drakon and not errors:
            vertices, edges = graph
            items_by_id = {item["item_id"]: item for item in work}
            auto = Auto(name, vertices, edges, items_by_id, errors)
            if auto.run():
                originals = None if official else {item["item_id"]: item for item in items}
                result["drakon"] = to_widget(auto, items_by_id, originals)
    except ConversionError as exc:
        result["exception"] = str(exc)
    result["errors"] = [{"items": i, "message": m} for i, m in errors]
    return result


def convert_file(path, official=False):
    for diagram_id, name, is_drakon, items in read_drn(path):
        record = convert_diagram(name, is_drakon, items, official)
        record["diagram_id"] = diagram_id
        yield record


def main(argv):
    official = "--official" in argv
    argv = [a for a in argv if a != "--official"]
    if len(argv) >= 3 and argv[0] == "--pretty":
        for record in convert_file(argv[1], official):
            if record["name"] == argv[2]:
                print(json.dumps(record.get("drakon", record), indent=2, ensure_ascii=False))
                return 0
        print("diagram not found: %s" % argv[2], file=sys.stderr)
        return 1
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    for path in argv:
        for record in convert_file(path, official):
            record["file"] = path
            print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
