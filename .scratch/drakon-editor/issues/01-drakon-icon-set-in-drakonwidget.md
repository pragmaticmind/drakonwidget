# DRAKON icon set in drakonwidget

Type: research
Status: resolved
Blocked by:

## Question

Which DRAKON icons (and structural constructs, e.g. primitive vs silhouette, branches, loops, parallel, insertion, comments) does drakonwidget support, and what are each one's semantics, allowed content, and placement rules? Produce the exhaustive list from the drakonwidget source (`dtsrc/`, `static/js/`, `README.md`); this list is the icon baseline for the new editor.

## Answer

On `type:"drakon"` Diagrams, drakonwidget v1.5.7 supports **27 stored DRAKON item types**, 2 virtual constructs, and 2 support types.

Stored DRAKON item types:
- Flow icons: `action`, `question`, `select`, `case`, `branch`, `end`, `insertion`, `comment`.
- Loops and parallel: `loopbegin`, `loopend`, `arrow-loop`, `parbegin`, `parend`.
- Input/output: `simpleinput`, `simpleoutput`, `input`, `output`.
- Two-part icons: `process`, `shelf`.
- Time: `timer`, `pause`, `duration`, `ctrlstart`, `ctrlend`.
- Other: `drakon-image`.
- Style-only reserved items: `header`, `params`. Their text comes from the Diagram's `name` and `params`.

Virtual constructs (never stored): `address` and `junction`.

Support types: `image` (bitmap store) and `connection`.

Type identifiers are the exact `items[id].type` strings in exportJson. Insert *operation* names expand into several stored items:
- `select` → `select` + 3 × `case`
- `foreach` → `loopbegin` + `loopend`
- `parblock` → 2 × `parbegin` + `parend`
- `par` / `firstpar` → one extra `parbegin`

Structure is a graph of string-id links:
- `one` = down, `two` = right.
- Question: `one`/`two` are the two exits. `flag1` truthy means down = Yes.
- Choice: `select.one` points to the first case; cases chain left to right via `two`.
- Parallel: `parbegin` paths chain via `two` and join at `parend`.
- FOR loop: `loopbegin`/`loopend` are paired implicitly by nesting on the same vertical line.
- Arrow loop: `arrow-loop.one` is a back-link up to an earlier icon.
- Duration: attached on the left via the host's `side` field.
- Address (branch jump): implied whenever `one`/`two` references a `branch` id.
- Primitive vs silhouette: one `branch` vs two or more, ordered by `branchId`.

Content:
- `content` is a string, formatted per Diagram (`textFormat`: plain/markdown/html).
- `secondary` (upper text) exists only on `shelf`, `process`, `input`, `output`.
- `link` and `style` (a JSON string) are available on most icons.

Grammar:
- Insertion is allowed only on `down` edges and on right edges that turn down.
- Liana re-routing only goes down or right, with no crossings. The only upward paths are `arrow-loop` and backward Addresses.
- Liana and arrow edits stay within the same FOR loop.
- Duration can attach only to 10 host types, one per host.
- A `select` keeps at least 2 cases, and its first case is fixed.
- A silhouette keeps at least 2 branches.
- There is at most one `end`.

Gaps for the new Model:
- `insertion` refers to another Diagram by name text, not by id.
- `comment` is an inline flow icon, not a side note.
- `textFormat` is set per Diagram, not per item.
- The DRAKON-relevant free icon `group-duration` needs coordinates.
- The dtsrc corpus contains `two:""` (empty) and an unsupported drakon.tech type `sinput`.

Context: full findings with file:line citations are in `/home/dev/projects/drakonwidget-research-icons/research/drakon-icon-set.md` on branch `research/drakon-icon-set` (commit 7e99f94, not pushed).
