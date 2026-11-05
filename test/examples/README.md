# DRAKON example corpus

Real-world DRAKON diagrams, used to check whether they can be represented in the text syntax (see `prototypes/text-syntax`). Structurally identical diagrams (same structure, ignoring text) are stored once. `manifest.json` lists every file with origin, format and feature tags.

The widget-format sources (drakonhub_desktop, drakonwidget, drakon.tech.desktop) are released under The Unlicense. The DRAKON Editor sources come from pragmaticmind/drakon_editor, a fork of stepan-mitkin/drakon_editor. That repo has no LICENSE file and GitHub detects no license, so confirm its terms before redistributing the `drn/` files outside this repo.

## Formats

- `drakon-json`: one diagram per file, the DrakonWidget/DrakonTech JSON format (`items`, `one`/`two` links, `keywords`, `params`). This is what `prototypes/text-syntax/dump.py` reads.
- `drakon-json-lines`: the same diagrams, one per line, wrapped as `{origin, nodes, features, diagram}`.
- `drn-items`: DRAKON Editor `.drn` files. A `.drn` is an SQLite database whose diagrams are stored as drawn geometry (icons and lines with x/y/w/h, arrows), not as a node graph. These files export each diagram's `items` table rows unchanged (null columns omitted), plus the diagram name, description and info. Older `.drn` versions lack some columns, so `columns` lists the ones present.
- `drn-converted-lines`: the `.drn` diagrams converted to `drakon-json` by `tools/drn2graph.py`, one per line: `{origin, name, status, drn_file, ...}`. When `status` is `converted` the line has `nodes`, `features` and `diagram` (widget JSON). When it is `rejected` the line has the `errors` DRAKON Editor shows for that diagram; these make good negative tests. `not-drakon` lines are free-form diagrams, which are only checked for geometry errors.

## Sources

Widget-format (`drakon-json`, `drakon-json-lines`):
- `drakonhub/` (16): `drakon_examples` in drakonhub_desktop. Real-life flowcharts with headers, comments, callouts, durations and styles.
- `drakonwidget/` (7): `js/examples.js` in drakonwidget. The only parallel (`parbegin`/`parend`), `insertion` and `group-duration` samples in this format.
- `drakontech/` (124): `examples` in drakon.tech.desktop. Loops, select/case, silhouettes, state machines and classes. Upstream repeats each diagram per target language, so duplicates were removed.
- `drakonwidget-dtsrc.jsonl` (807): the widget's own source in `dtsrc/`, written in Drakon-JavaScript. Larger diagrams (up to 97 nodes) than the examples above, but no new icon types.

DRAKON Editor (`drn-items`, in `drn/`):
- 3321 distinct diagrams from 189 of the 195 `.drn` files (5 of the others only contain duplicates of diagrams already stored, 1 has no diagrams): `examples`, `testdata`, `unittest`, `generators`, `docs` and the editor's own source in drakon_editor, plus the `src/static/*.drn` sources of drakon.tech.desktop. `testdata` is mostly small diagrams (median 7 items, largest 102).
- `drn-converted.jsonl`: the same 3321 diagrams after conversion. 3097 converted, 143 rejected because they break a DRAKON rule (139 of them are error cases in `testdata`; the most common errors are dangling lines, misplaced lines and a missing end), 81 not DRAKON diagrams.

## Feature coverage

Widget-format (unique diagrams, excluding dtsrc): question 83, silhouette 32, loopbegin/loopend 30, flipped Yes/No 34, arrow-loop 22, select 22, case 22, header 16, action side-link 11, style 9, sinput 6, comment 4, callout 4, duration 2, insertion 2, async 2, parbegin/parend 1, group-duration 1.

dtsrc: question 511, flipped Yes/No 325, silhouette 148, loopbegin/loopend 176, case/select 70 each, arrow-loop 18, async 11, sinput 9.

`.drn` (icon names are the editor's): if 1348, loopstart/loopend 643/642, silhouette 395, arrow 483, address 397, case/select 298 each, shelf 230, commentout 56, commentin 41, insertion 10, output 2, input 1, pause 1.

`.drn` converted to widget format (diagrams): question 1295, flipped Yes/No 857, loopbegin/loopend 626, silhouette 363, case/select 270 each, shelf 154, arrow-loop 85, insertion 5, output 2, input 1. This adds far more arrow loops and silhouettes than the other sources.

## Differences between the two icon vocabularies

- `.drn` draws addresses as icons; the widget format models them as links to `branch` items. `.drn` comments (`commentin`/`commentout`) are not part of the flow and are dropped by the conversion, as DRAKON Editor's own exporter does.
- `.drn` stores Yes/No placement and line routing as geometry. The widget format stores it as `flag1` and `one`/`two` links, and arrow loops as `arrow-loop` items.
- Both have `shelf`, `insertion`, `input`, `output`, `process` and `pause`. A shelf's second text is `text2` in `.drn` and `secondary` in the widget format.

## Converting `.drn` files: `tools/drn2graph.py`

`drn2graph.py` turns the drawn geometry of a `.drn` diagram into the widget graph. It is a Python port (standard library only) of DRAKON Editor's own pipeline in pragmaticmind/drakon_editor:

1. `scripts/graph2.tcl`: cut lines at icons and at each other, merge collinear pieces, attach line ends to icon sides, add knots where lines meet.
2. `scripts/auto.tcl`: walk the knots into ordered links, build branches, check the DRAKON rules, pair loops, skip knots.
3. `generators/drakon_tech.tcl` (`convert_diagram`): write DrakonTech/DrakonWidget items. This is the exporter behind `drakon_gen.tcl -dt 1`.

Each diagram is converted on its own. A diagram that breaks a rule gets the same error messages DRAKON Editor shows.

Usage: `python3 tools/drn2graph.py FILE.drn` prints one JSON object per diagram; `--pretty FILE.drn NAME` prints one diagram's widget JSON. Pass `--official` to get exactly what DRAKON Editor's exporter writes. Without it, two things the exporter throws away are kept: `insertion`/`input`/`output`/`process` icons keep their type (the exporter writes `action`), and `text2` becomes `secondary`.

Deliberate differences from the original, where it is wrong (marked `FIX` in the code):

- Branches are numbered left to right. The original uses Tcl hash order.
- `branchId` comes from the branch itself. The original crashes (`Invalid number`) when the icon below a branch header is a knot.
- The start icon of a silhouette is never exported as an item.
- Two arrow loops entering one above the other become a chain (outer arrow-loop, inner arrow-loop, icon). The original points the outer one at `""`.
- The loop-entry check is memoised, so it cannot take exponential time.

### How it was validated

`tools/oracle/` runs DRAKON Editor itself as a reference and compares the two, diagram by diagram, on all 3796 diagrams in the 195 `.drn` files (before removing duplicates):

- 3555 converted diagrams are identical.
- 139 rejected diagrams have the same errors. 2 more have the same error on the other icon of an overlapping pair (Tcl hash order).
- 89 non-DRAKON diagrams have the same errors.
- 2 diagrams crash the original (`Invalid number`) and convert in the port; 1 has the nested arrow loops above.
- 8 diagrams are in `testdata/base1.drn`, which is so old the original cannot read it (no `text2` column, no `tree_nodes` table). With both added to a copy, all 8 match.

To repeat it (needs `tcl tcllib libsqlite3-tcl`, and the drakon_editor and drakon.tech.desktop repos cloned to `/tmp`):

```
python3 tools/oracle/run_reference.py /tmp/drakon_editor /tmp/reference.jsonl drakon_editor=/tmp/drakon_editor drakon.tech.desktop=/tmp/drakon.tech.desktop
python3 tools/oracle/compare_reference.py /tmp/reference.jsonl drakon_editor=/tmp/drakon_editor drakon.tech.desktop=/tmp/drakon.tech.desktop
```

`compare_reference.py` exits non-zero on any difference that is not listed above. The unit tests (`python3 -m unittest discover -s tools`) draw small diagrams into temporary `.drn` files: sequence, parameters, questions both ways, foreach loop, arrow loop, select with default, silhouette with address, preserved types, shelf `secondary`, and error cases. The same diagrams were also run through the reference, and they agree.

## Notes for validation

- Merged flows (several icons pointing at one icon) and arrow-loop back-edges are the likely hard cases for a tree-like text syntax.
- Layout coordinates (callouts, `.drn` geometry) and per-icon `style` are probably not round-trippable and may need to be dropped or kept as optional attributes.

## Regenerating

`tools/collect_extra.py DRAKONWIDGET_DIR DRAKON_EDITOR_DIR [DRAKON_TECH_DESKTOP_DIR]` rebuilds `drakonwidget-dtsrc.jsonl`, `drn/`, `drn-converted.jsonl` and the matching `manifest.json` entries. The per-diagram files in `drakonhub/`, `drakonwidget/` and `drakontech/` were produced by an earlier one-off extraction and are not regenerated by this script.
