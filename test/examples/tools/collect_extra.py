#!/usr/bin/env python3
"""Collect extra DRAKON examples into test/examples.

Usage:
  collect_extra.py DRAKONWIDGET_DIR DRAKON_EDITOR_DIR [DRAKON_TECH_DESKTOP_DIR]

Adds:
  drakonwidget-dtsrc.jsonl   widget-format diagrams from <DRAKONWIDGET_DIR>/dtsrc
  drn/<name>.json            diagrams exported from DRAKON Editor .drn (SQLite) files
  drn-converted.jsonl        the same .drn diagrams converted to widget format by
                             drn2graph.py, or the errors DRAKON Editor would show
and appends entries to manifest.json. Existing entries are kept; re-running
replaces every entry that is not format "drakon-json".

Diagrams already present (same structure, ignoring text) are skipped, so the
corpus has no duplicates.
"""
import collections
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)  # test/examples
sys.path.insert(0, HERE)
import drn2graph  # noqa: E402


def widget_sig(d):
    return hashlib.md5(json.dumps(
        {k: {a: b for a, b in v.items() if a != "content"} for k, v in d["items"].items()},
        sort_keys=True).encode()).hexdigest()


def widget_features(d):
    it = d["items"]
    t = collections.Counter(i["type"] for i in it.values())
    g = set(t) - {"action", "end", "branch"}
    if t["branch"] > 1:
        g.add("silhouette")
    if any(i["type"] == "question" and i.get("flag1") == 0 for i in it.values()):
        g.add("flipped-yes-no")
    if d.get("keywords", {}).get("machine"):
        g.add("machine")
    if d.get("keywords", {}).get("async"):
        g.add("async")
    return sorted(g)


DRN_COLS = ["item_id", "type", "text", "x", "y", "w", "h", "a", "b", "aux_value", "color", "format", "text2"]


def drn_features(items):
    t = collections.Counter(i["type"] for i in items)
    g = set(t) - {"action", "beginend", "vertical", "horizontal", "branch"}
    if t["branch"] > 1:
        g.add("silhouette")
    return sorted(g)


def drn_sig(rows):
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    widget_dir, editor_dir = sys.argv[1], sys.argv[2]
    tech_dir = sys.argv[3] if len(sys.argv) > 3 else None

    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf8"))
    manifest = [m for m in manifest if m.get("format", "drakon-json") == "drakon-json"]
    for m in manifest:
        m.setdefault("format", "drakon-json")

    seen = set()
    for m in manifest:
        d = json.load(open(os.path.join(OUT, m["file"]), encoding="utf8"))
        seen.add(widget_sig(d))

    # 1. widget-format diagrams from the widget's own source
    lines = []
    counts = collections.Counter()
    for p in sorted(glob.glob(os.path.join(widget_dir, "dtsrc", "**", "*.drakon"), recursive=True)):
        d = json.load(open(p, encoding="utf8"))
        if d.get("type") != "drakon" or "items" not in d:
            continue
        s = widget_sig(d)
        if s in seen:
            continue
        seen.add(s)
        origin = os.path.relpath(p, widget_dir)
        feats = widget_features(d)
        counts.update(feats)
        lines.append(json.dumps({"origin": origin, "nodes": len(d["items"]), "features": feats, "diagram": d},
                                ensure_ascii=False))
    with open(os.path.join(OUT, "drakonwidget-dtsrc.jsonl"), "w", encoding="utf8") as f:
        f.write("\n".join(lines) + "\n")
    manifest.append({"file": "drakonwidget-dtsrc.jsonl", "source": "drakonwidget-dtsrc", "format": "drakon-json-lines",
                     "diagrams": len(lines), "features": dict(sorted(counts.items()))})

    # 2. DRAKON Editor .drn files (SQLite, layout based)
    # 3. ...and the same diagrams converted to widget format
    drn_seen = set()
    roots = [("drakon_editor", editor_dir)]
    if tech_dir:
        roots.append(("drakon.tech.desktop", tech_dir))
    used = set()
    converted_lines = []
    status_counts = collections.Counter()
    converted_features = collections.Counter()
    for label, root in roots:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.drn"), recursive=True)):
            origin = label + "/" + os.path.relpath(p, root)
            graph_input = {did: (name, is_drakon, items) for did, name, is_drakon, items in drn2graph.read_drn(p)}
            file_lines = []
            c = sqlite3.connect(p)
            tables = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}
            if "items" not in tables or "diagrams" not in tables:
                continue
            # Older .drn versions lack some columns (color, format, text2) and tables.
            have = {r[1] for r in c.execute("pragma table_info(items)")}
            cols = [k for k in DRN_COLS if k in have]
            dcols = {r[1] for r in c.execute("pragma table_info(diagrams)")}
            dsel = ",".join(k if k in dcols else "null" for k in ("diagram_id", "name", "origin", "description", "zoom"))
            diagrams = []
            fcounts = collections.Counter()
            for did, name, dorigin, desc, zoom in c.execute("select %s from diagrams order by diagram_id" % dsel).fetchall():
                rows = c.execute("select %s from items where diagram_id=? order by item_id" % ",".join(cols),
                                 (did,)).fetchall()
                rows = [dict(zip(cols, r)) for r in rows]
                geo = sorted((r["type"], r.get("x"), r.get("y"), r.get("w"), r.get("h"), r.get("a"), r.get("b")) for r in rows)
                s = drn_sig(geo)
                if s in drn_seen:
                    continue
                drn_seen.add(s)
                items = [{k: v for k, v in r.items() if v is not None} for r in rows]
                feats = drn_features(items)
                fcounts.update(feats)
                info = {}
                if "diagram_info" in tables:
                    info = dict(c.execute("select name,value from diagram_info where diagram_id=?", (did,)).fetchall())
                diagrams.append({"name": name, "origin": dorigin, "description": desc, "info": info,
                                 "nodes": len(items), "features": feats, "items": items})
                gname, is_drakon, gitems = graph_input[did]
                rec = drn2graph.convert_diagram(gname, is_drakon, gitems)
                if "drakon" in rec:
                    status = "converted"
                elif not is_drakon:
                    status = "not-drakon"
                elif "exception" in rec:
                    status = "exception"
                else:
                    status = "rejected"
                status_counts[status] += 1
                line = {"origin": origin, "name": name, "status": status}
                if status == "converted":
                    gfeats = widget_features(rec["drakon"])
                    converted_features.update(gfeats)
                    line.update({"nodes": len(rec["drakon"]["items"]), "features": gfeats, "diagram": rec["drakon"]})
                else:
                    line["errors"] = rec["errors"]
                    if "exception" in rec:
                        line["exception"] = rec["exception"]
                file_lines.append(line)
            if not diagrams:
                continue
            file_info = dict(c.execute("select key,value from info").fetchall()) if "info" in tables else {}
            base = re.sub(r"[^\w.]+", "-", os.path.splitext(os.path.relpath(p, root))[0], flags=re.U).strip("-").lower()
            rel = "drn/%s__%s.json" % (label.replace(".", "-"), base)
            k = 2
            while rel in used:
                rel = rel.replace(".json", "-%d.json" % k)
                k += 1
            used.add(rel)
            write_json(os.path.join(OUT, rel), {"format": "drn-items", "origin": origin, "info": file_info,
                                                "columns": cols, "diagrams": diagrams})
            manifest.append({"file": rel, "source": label, "origin": origin, "format": "drn-items",
                             "diagrams": len(diagrams), "features": dict(sorted(fcounts.items()))})
            for line in file_lines:
                line["drn_file"] = rel
                converted_lines.append(json.dumps(line, ensure_ascii=False))

    with open(os.path.join(OUT, "drn-converted.jsonl"), "w", encoding="utf8") as f:
        f.write("\n".join(converted_lines) + "\n")
    manifest.append({"file": "drn-converted.jsonl", "source": "drn-converted", "format": "drn-converted-lines",
                     "diagrams": len(converted_lines), "status": dict(sorted(status_counts.items())),
                     "features": dict(sorted(converted_features.items()))})

    write_json(manifest_path, manifest)
    print("widget-dtsrc diagrams:", len(lines))
    print("drn files:", sum(1 for m in manifest if m["format"] == "drn-items"),
          "drn diagrams:", sum(m["diagrams"] for m in manifest if m["format"] == "drn-items"))
    print("drn converted:", dict(sorted(status_counts.items())))


if __name__ == "__main__":
    main()
