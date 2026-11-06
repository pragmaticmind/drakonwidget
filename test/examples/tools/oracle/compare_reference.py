#!/usr/bin/env python3
"""Compare drn2graph.py with DRAKON Editor's own pipeline, diagram by diagram.

Usage:
  compare_reference.py REFERENCE.jsonl LABEL=DIR [LABEL=DIR ...] [--show N]

REFERENCE.jsonl comes from run_reference.py; the LABEL=DIR pairs must be the
same as the ones given to it. Prints a summary and exits non-zero when a
difference is found that is not one of the documented deliberate fixes.

Before comparing, both outputs are put in a canonical form:
  - generated ids (arrow-loop items, the synthetic branch 0 of a primitive
    diagram) are replaced by names derived from what they point to;
  - Tcl's "{}" for an empty item list is read as "";
  - branchId values are compared on their own, because drn2graph numbers
    branches left to right and the original uses Tcl hash order.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import drn2graph  # noqa: E402


def norm_items(items):
    items = str(items).strip()
    if items in ("{}", ""):
        return ""
    return items.strip("{}")


def error_set(record):
    return sorted((norm_items(e["items"]), e["message"]) for e in record.get("errors", []))


def canonical(drakon):
    """Return (items without branchId, branch order, params)."""
    items = drakon.get("items", {})
    rename = {}
    for key, item in items.items():
        if item.get("type") == "branch" and item.get("branchId") == 0:
            rename[key] = "branch0"

    def arrow_name(key, depth=0):
        target = str(items[key].get("one"))
        if depth < 10 and items.get(target, {}).get("type") == "arrow-loop":
            target = arrow_name(target, depth + 1)
        return "arrow->" + target

    for key, item in items.items():
        if item.get("type") == "arrow-loop":
            rename[key] = arrow_name(key)
    out = {}
    branch_order = []
    for key, item in items.items():
        item = dict(item)
        for field in ("one", "two"):
            if field in item and item[field] in rename:
                item[field] = rename[item[field]]
        if item.get("type") == "branch":
            branch_order.append((item.get("branchId"), item.get("content", "")))
            item.pop("branchId", None)
        out[rename.get(key, key)] = item
    order = [name for _, name in sorted(branch_order, key=lambda p: (str(p[0]) if p[0] == "" else "%09d" % p[0]))]
    return out, order, drakon.get("params")


def compare_drakon(ref, port):
    """Classify the differences between two converted diagrams."""
    ref_items, ref_order, ref_params = canonical(ref)
    port_items, port_order, port_params = canonical(port)
    kinds = []
    # Official bug: the silhouette start icon is exported as an "end" item
    # when branch 1 is not the branch under it.
    extra = set(ref_items) - set(port_items)
    stray_start = {k for k in extra if ref_items[k].get("type") == "end" and not drn2graph.is_end(ref_items[k].get("content"))}
    if stray_start:
        kinds.append("fix:start-icon-exported")
        for k in stray_start:
            ref_items.pop(k)
    if ref_order != port_order:
        kinds.append("fix:branch-order")
    ref_ids = sorted(str(b.get("branchId")) for b in ref.get("items", {}).values() if b.get("type") == "branch")
    if "" in ref_ids or "None" in ref_ids:
        kinds.append("fix:branch-id-missing")
    # Arrow loops that pointed at a knot ("") in the original.
    if any(k == "arrow->" for k in ref_items):
        kinds.append("fix:arrow-loop-to-knot")
        ref_items = {k: v for k, v in ref_items.items() if not k.startswith("arrow->")}
        port_items = {k: v for k, v in port_items.items() if not k.startswith("arrow->")}
        for items in (ref_items, port_items):
            for item in items.values():
                for field in ("one", "two"):
                    if str(item.get(field, "")).startswith("arrow->"):
                        item[field] = "arrow"
    if ref_params != port_params:
        kinds.append("diff:params")
    if ref_items != port_items:
        kinds.append("diff:items")
    return kinds, ref_items, port_items


def main():
    args = [a for a in sys.argv[1:]]
    show = 5
    if "--show" in args:
        i = args.index("--show")
        show = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    reference = collections.defaultdict(dict)
    file_errors = {}
    for line in open(args[0], encoding="utf-8"):
        rec = json.loads(line)
        if "file_error" in rec:
            file_errors[rec["origin"]] = rec["file_error"]
            continue
        reference[rec["origin"]][rec["diagram_id"]] = rec
    roots = dict(a.split("=", 1) for a in args[1:])

    counts = collections.Counter()
    examples = collections.defaultdict(list)
    for origin in sorted(reference):
        label, rel = origin.split("/", 1)
        path = os.path.join(roots[label], rel)
        port = {rec["diagram_id"]: rec for rec in drn2graph.convert_file(path, official=True)}
        for diagram_id, ref in reference[origin].items():
            mine = port.get(diagram_id)
            where = "%s #%s %s" % (origin, diagram_id, ref["name"])
            if mine is None:
                counts["diff:missing-in-port"] += 1
                examples["diff:missing-in-port"].append(where)
                continue
            if not ref["is_drakon"]:
                counts["not-drakon"] += 1
                if error_set(ref) != error_set(mine):
                    counts["diff:errors(non-drakon)"] += 1
                    examples["diff:errors(non-drakon)"].append((where, error_set(ref), error_set(mine)))
                continue
            ref_ok, port_ok = "drakon" in ref, "drakon" in mine
            if "exception" in ref or "exception" in mine:
                key = "exception ref=%s port=%s" % ("exception" in ref, "exception" in mine)
                ref_exc = ref.get("exception", "")
                if "exception" not in mine and ("no such column" in ref_exc or "no such table" in ref_exc):
                    # Old file without text2 or tree_nodes: the original cannot
                    # read it. Add them to a copy to check these diagrams.
                    key = "original-cannot-read-old-schema"
                elif ref_exc.startswith("Invalid number") and port_ok:
                    key = "fix:branch-id-missing"
                elif "exception" in ref and port_ok:
                    key = "fix:exception-in-original"
                counts[key] += 1
                examples[key].append((where, ref.get("exception"), mine.get("exception"), error_set(mine)))
                continue
            if not ref_ok and not port_ok:
                if error_set(ref) == error_set(mine):
                    counts["same errors"] += 1
                elif [m for _, m in error_set(ref)] == [m for _, m in error_set(mine)]:
                    counts["same error messages, other item"] += 1
                else:
                    counts["diff:errors"] += 1
                    examples["diff:errors"].append((where, error_set(ref), error_set(mine)))
                continue
            if ref_ok != port_ok:
                key = "diff:only-%s-converts" % ("reference" if ref_ok else "port")
                counts[key] += 1
                examples[key].append((where, error_set(ref), error_set(mine)))
                continue
            kinds, ref_items, port_items = compare_drakon(ref["drakon"], mine["drakon"])
            if not kinds:
                counts["identical"] += 1
            for kind in kinds:
                counts[kind] += 1
                if kind.startswith("diff:"):
                    diff = {k: (ref_items.get(k), port_items.get(k)) for k in set(ref_items) | set(port_items)
                            if ref_items.get(k) != port_items.get(k)}
                    examples[kind].append((where, diff))
                else:
                    examples[kind].append(where)

    print("reference files that failed to run:", len(file_errors))
    for name, error in file_errors.items():
        print("   ", name, "-", error.splitlines()[0] if error else "")
    for key, value in sorted(counts.items()):
        print("%-45s %d" % (key, value))
    for key in sorted(examples):
        if key.startswith("diff:") or key.startswith("exception"):
            print("\n==", key)
            for example in examples[key][:show]:
                print("  ", json.dumps(example, ensure_ascii=False)[:1500])
    bad = sum(v for k, v in counts.items() if k.startswith("diff:") or k.startswith("exception ref=False"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
