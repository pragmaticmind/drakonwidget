# Model shape: tree or graph

Type: grilling
Status: resolved
Blocked by: 02

## Question

Should the Model mirror DRAKON's structure as a tree (silhouette → branches → sequences, making most Grammar violations unrepresentable) or be a graph of nodes and edges (more standard, but needing a validator), and which existing format, if any, should it adopt or align with?

## Answer

Resolved by grilling, informed by the prototype (draft PR pragmaticmind/drakonwidget#1, `prototypes/model-format/`).

1. **Shape**: the Model is stored as a **graph**: Icons with named exits. The editor also derives a canonical tree from the graph for the Text view, layout and validation. Grammar enforcement means every committed edit must yield a graph the tree can be derived from.
2. **Format**: a project-specific **Schema** (prototype option A). It uses drakonwidget concepts with cleaned-up naming, borrows BPMN's separate, id-keyed layout section, and has a published `$id` plus `schemaVersion`. The Model does not need to validate as JSON Graph Format for now (parked in the fog). JSON Graph Format can be an export plugin.
3. **Field names**: as in the prototype: `next`, `yes`, `no`, `down` (which exit is drawn downwards), `cases` (ordered), `end` (loop pairing), `branch` (address target), `secondaryText`, `diagram` (insertion target id).
4. **Explicit constructs**: the `address` Icon is stored explicitly and points at a branch id. Loop pairing is stored explicitly as `loopbegin.end`.
5. **Branches**: an ordered top-level array `[{ id, name, first }]`. Array order is left-to-right column order. A primitive Diagram is a one-branch array whose `name` may be empty. The validator checks that only the last branch reaches End and that every other branch ends in addresses.
6. **Identity**: the Model carries `schemaVersion` and a stable Diagram `id`. The Host assigns the `id`; if it is missing, the editor generates a UUID and reports it via `onChange`. Icon ids are internal, unique within a Diagram, and never reused.
7. **Text format**: set once per Diagram, default `markdown`.
8. **Metadata**: an optional free-form `meta` object on every Icon and on the Diagram. The editor preserves it and never interprets it.
9. **Free icons**: `group-duration` is left out until Coordinates section semantics decides how stored positions work.
10. **Vocabulary**: **Icon** is the term for one DRAKON element in a Diagram.

Evidence: a lossless round trip between option A and option B; option A's schema alone catches 8 of 9 expressible faults versus 5 of 9 for the JSON Graph Format profile, and makes duplicate exits and ambiguous case order unwritable; option A is about half the size.

### Addendum: shared joins (2026-10-31)

The derived structure is a **tree plus downward join references**, not a pure tree. An exit may point at an Icon that other exits also reach (a shared join), so the Model needs no new field. The Grammar rule becomes: the derived tree, with its downward joins, must be drawable without crossing lines. This keeps every legal DRAKON Diagram expressible, and keeps drakonwidget import from rejecting Diagrams that contain such joins.