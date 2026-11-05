"""Unit tests for drn2graph.py.

Each test draws a small diagram the way DRAKON Editor stores it (icons with a
centre and half-sizes, separate line items) into a temporary .drn file and
checks the converted graph.

Run: python3 -m unittest discover -s test/examples/tools
"""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drn2graph  # noqa: E402

RIGHT_ARROW = 20100
LEFT_ARROW = 40100


class Drn:
    """Writes a minimal .drn file. Coordinates follow DRAKON Editor:
    icons are (centre x, centre y, half width, half height); a vertical line
    is (x, top y, length); a horizontal line is (left x, y, length)."""

    def __init__(self, old_schema=False):
        fd, self.path = tempfile.mkstemp(suffix=".drn")
        os.close(fd)
        self.db = sqlite3.connect(self.path)
        extra = "" if old_schema else ", color text, format text, text2 text"
        self.db.executescript("""
            create table info (key text primary key, value text);
            create table diagrams (diagram_id integer primary key, name text unique,
                origin text, description text, zoom double);
            create table items (item_id integer primary key, diagram_id integer, type text,
                text text, selected integer, x integer, y integer, w integer, h integer,
                a integer, b integer, aux_value integer%s);
            create table tree_nodes (node_id integer primary key, parent integer,
                type text, name text, diagram_id integer);
            insert into info values ('type', 'drakon');
            insert into info values ('version', '5');
        """ % extra)
        self.diagram_id = 0
        self.next_item = 0

    def diagram(self, name, tree_type="item"):
        self.diagram_id += 1
        self.db.execute("insert into diagrams (diagram_id, name) values (?, ?)", (self.diagram_id, name))
        self.db.execute("insert into tree_nodes (parent, type, name, diagram_id) values (0, ?, ?, ?)",
                        (tree_type, name, self.diagram_id))
        return self

    def item(self, type_, text, x, y, w, h, a=0, b=0):
        self.next_item += 1
        self.db.execute(
            "insert into items (item_id, diagram_id, type, text, selected, x, y, w, h, a, b) "
            "values (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)",
            (self.next_item, self.diagram_id, type_, text, x, y, w, h, a, b))
        return str(self.next_item)

    def icon(self, type_, text, x, y, w=50, h=20, a=0, b=0):
        return self.item(type_, text, x, y, w, h, a, b)

    def vline(self, x, y1, y2, a=0):
        return self.item("vertical", "", x, y1, 0, y2 - y1, a)

    def hline(self, x1, x2, y, a=0):
        return self.item("horizontal", "", x1, y, x2 - x1, 0, a)

    def convert(self):
        self.db.commit()
        return {rec["name"]: rec for rec in drn2graph.convert_file(self.path)}

    def close(self):
        self.db.close()
        os.remove(self.path)


def branch0(items):
    """The synthetic branch of a primitive diagram."""
    [b] = [i for i in items.values() if i["type"] == "branch"]
    return b


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.drn = Drn()

    def tearDown(self):
        self.drn.close()

    def ok(self, name):
        record = self.drn.convert()[name]
        self.assertEqual(record["errors"], [], record)
        self.assertIn("drakon", record)
        return record["drakon"]["items"]

    def errors(self, name):
        record = self.drn.convert()[name]
        self.assertNotIn("drakon", record)
        return [(e["items"], e["message"]) for e in record["errors"]]

    def test_primitive_sequence(self):
        d = self.drn.diagram("seq")
        d.icon("beginend", "seq", 100, 40)
        a = d.icon("action", "A", 100, 120)
        end = d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        items = self.ok("seq")
        self.assertEqual(branch0(items)["one"], a)
        self.assertEqual(items[a], {"type": "action", "content": "A", "one": end})
        self.assertEqual(items[end], {"type": "end", "content": "End"})
        self.assertEqual(len(items), 3)  # the start icon is not an item

    def test_parameters_icon_becomes_params(self):
        d = self.drn.diagram("withParams")
        d.icon("beginend", "withParams", 100, 40)
        d.icon("action", "left\nright", 250, 40)
        d.hline(150, 200, 40)
        d.icon("action", "A", 100, 120)
        d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        record = self.drn.convert()["withParams"]
        self.assertEqual(record["drakon"]["params"], "left\nright")
        self.assertEqual(len(record["drakon"]["items"]), 3)

    def test_question_merges_below(self):
        d = self.drn.diagram("q")
        d.icon("beginend", "q", 100, 40)
        q = d.icon("if", "c", 100, 120, a=100, b=1)  # yes drawn down
        down = d.icon("action", "D", 100, 200)
        right = d.icon("action", "R", 250, 200)
        end = d.icon("beginend", "End", 100, 360)
        d.vline(100, 60, 340)
        d.vline(250, 120, 280)
        d.hline(100, 250, 280)
        items = self.ok("q")
        self.assertEqual(items[q], {"type": "question", "content": "c", "flag1": 1, "one": down, "two": right})
        self.assertEqual(items[down]["one"], end)
        self.assertEqual(items[right]["one"], end)

    def test_question_yes_to_the_right(self):
        d = self.drn.diagram("q0")
        d.icon("beginend", "q0", 100, 40)
        q = d.icon("if", "c", 100, 120, a=100, b=0)
        d.icon("action", "D", 100, 200)
        d.icon("action", "R", 250, 200)
        d.icon("beginend", "End", 100, 360)
        d.vline(100, 60, 340)
        d.vline(250, 120, 280)
        d.hline(100, 250, 280)
        self.assertEqual(self.ok("q0")[q]["flag1"], 0)

    def test_foreach_loop(self):
        d = self.drn.diagram("loop")
        d.icon("beginend", "loop", 100, 40)
        begin = d.icon("loopstart", "foreach x; xs", 100, 120)
        body = d.icon("action", "use(x)", 100, 200)
        finish = d.icon("loopend", "", 100, 280)
        end = d.icon("beginend", "End", 100, 360)
        d.vline(100, 60, 340)
        items = self.ok("loop")
        self.assertEqual(branch0(items)["one"], begin)
        self.assertEqual(items[begin], {"type": "loopbegin", "content": "x; xs", "one": body})
        self.assertEqual(items[body]["one"], finish)
        self.assertEqual(items[finish]["one"], end)

    def test_arrow_loop(self):
        d = self.drn.diagram("arrow")
        d.icon("beginend", "arrow", 100, 40)
        a = d.icon("action", "A", 100, 120)
        q = d.icon("if", "again?", 100, 200, a=100, b=0)
        end = d.icon("beginend", "End", 100, 300)
        d.vline(100, 60, 280)
        d.item("arrow", "", 250, 80, 150, 120, 0, 0)  # up the right side, back left at y=80
        items = self.ok("arrow")
        [loop_id] = [k for k, i in items.items() if i["type"] == "arrow-loop"]
        self.assertEqual(items[loop_id]["one"], a)
        self.assertEqual(branch0(items)["one"], loop_id)
        self.assertEqual(items[a]["one"], q)
        self.assertEqual(items[q]["one"], end)
        self.assertEqual(items[q]["two"], loop_id)

    def test_select_with_default(self):
        d = self.drn.diagram("sel")
        d.icon("beginend", "sel", 100, 40)
        s = d.icon("select", "x", 100, 120)
        cases = [d.icon("case", t, x, 200) for t, x in (("1", 100), ("2", 250), ("", 400))]
        acts = [d.icon("action", "A%d" % i, x, 260) for i, x in enumerate((100, 250, 400))]
        end = d.icon("beginend", "End", 100, 400)
        d.vline(100, 60, 380)
        d.hline(100, 400, 160)
        d.hline(100, 400, 320)
        d.vline(250, 160, 320)
        d.vline(400, 160, 320)
        items = self.ok("sel")
        self.assertEqual(items[s]["one"], cases[0])
        self.assertEqual(items[cases[0]], {"type": "case", "content": "1", "one": acts[0], "two": cases[1]})
        self.assertEqual(items[cases[1]], {"type": "case", "content": "2", "one": acts[1], "two": cases[2]})
        self.assertEqual(items[cases[2]], {"type": "case", "content": "", "one": acts[2]})
        for act in acts:
            self.assertEqual(items[act]["one"], end)

    def test_silhouette_with_address(self):
        d = self.drn.diagram("sil")
        d.icon("beginend", "sil", 200, 40)
        b1 = d.icon("branch", "one", 200, 140)
        a1 = d.icon("action", "A1", 200, 220)
        d.icon("address", "two", 200, 300)
        b2 = d.icon("branch", "two", 400, 140)
        a2 = d.icon("action", "A2", 400, 220)
        end = d.icon("beginend", "End", 400, 300)
        d.vline(200, 60, 400)
        d.vline(400, 100, 280)
        d.hline(50, 200, 100, RIGHT_ARROW)
        d.hline(200, 400, 100)
        d.vline(50, 100, 400)
        d.hline(50, 200, 400)
        items = self.ok("sil")
        self.assertEqual(items[b1], {"type": "branch", "content": "one", "branchId": 1, "one": a1})
        self.assertEqual(items[b2], {"type": "branch", "content": "two", "branchId": 2, "one": a2})
        self.assertEqual(items[a1]["one"], b2)  # the address stands for branch "two"
        self.assertEqual(items[a2]["one"], end)
        self.assertEqual(len(items), 5)  # no start item, no address item

    def test_insertion_keeps_its_type(self):
        d = self.drn.diagram("ins")
        d.icon("beginend", "ins", 100, 40)
        ins = d.icon("insertion", "callSomething", 100, 120)
        d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        self.assertEqual(self.ok("ins")[ins]["type"], "insertion")
        official = {r["name"]: r for r in drn2graph.convert_file(self.drn.path, official=True)}
        self.assertEqual(official["ins"]["drakon"]["items"][ins]["type"], "action")

    def test_shelf_second_text_becomes_secondary(self):
        d = self.drn.diagram("shelf")
        d.icon("beginend", "shelf", 100, 40)
        shelf = d.icon("shelf", "42", 100, 120)
        self.drn.db.execute("update items set text2 = 'answer' where item_id = ?", (shelf,))
        end = d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        items = self.ok("shelf")
        self.assertEqual(items[shelf], {"type": "shelf", "content": "42", "secondary": "answer", "one": end})
        official = {r["name"]: r for r in drn2graph.convert_file(self.drn.path, official=True)}
        self.assertNotIn("secondary", official["shelf"]["drakon"]["items"][shelf])

    def test_error_dangling_line(self):
        d = self.drn.diagram("dangling")
        d.icon("beginend", "dangling", 100, 40)
        d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        stray = d.vline(300, 60, 180)
        self.assertEqual(self.errors("dangling"), [(stray, "Line not connected to any icon.")])

    def test_error_no_end(self):
        d = self.drn.diagram("noEnd")
        d.icon("beginend", "noEnd", 100, 40)
        d.icon("action", "A", 100, 120)
        d.vline(100, 60, 100)
        self.assertEqual(self.errors("noEnd"), [("", "The diagram must have exactly one end.")])

    def test_error_overlapping_icons(self):
        d = self.drn.diagram("overlap")
        first = d.icon("beginend", "overlap", 100, 40)
        d.icon("action", "A", 100, 60)
        self.assertEqual(self.errors("overlap"), [(first, "No space between icons.")])

    def test_error_loopend_without_loopstart(self):
        d = self.drn.diagram("badLoop")
        d.icon("beginend", "badLoop", 100, 40)
        stray = d.icon("loopend", "", 100, 120)
        d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        self.assertEqual(self.errors("badLoop"), [(stray, "Icon 'loopend' not expected here.")])

    def test_icon_swallowing_a_line_breaks_connectivity(self):
        # Matches DRAKON Editor: a line fully inside an icon leaves a phantom
        # knot behind, and the diagram fails the connectivity check.
        d = self.drn.diagram("swallow")
        d.icon("beginend", "swallow", 100, 40)
        d.icon("action", "A", 300, 120)
        d.vline(300, 110, 130)
        d.icon("beginend", "End", 100, 200)
        d.vline(100, 60, 180)
        self.assertEqual(self.errors("swallow"), [("", "All icons must be connected together.")])

    def test_non_drakon_diagram_is_only_checked(self):
        d = self.drn.diagram("free", tree_type="free")
        d.icon("action", "A", 100, 120)
        record = self.drn.convert()["free"]
        self.assertFalse(record["is_drakon"])
        self.assertNotIn("drakon", record)
        self.assertEqual(record["errors"], [])


class OldSchemaTest(unittest.TestCase):
    def test_reads_files_without_text2_column(self):
        drn = Drn(old_schema=True)
        try:
            d = drn.diagram("old")
            d.icon("beginend", "old", 100, 40)
            d.icon("action", "A", 100, 120)
            d.icon("beginend", "End", 100, 200)
            d.vline(100, 60, 180)
            record = drn.convert()["old"]
            self.assertIn("drakon", record)
        finally:
            drn.close()


if __name__ == "__main__":
    unittest.main()
