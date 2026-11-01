# Survey of existing diagram data formats

Type: research
Status: resolved
Blocked by: 01

## Question

How do existing formats (drakonwidget JSON, drakon.tech, Mermaid's flowchart model, JSON Graph Format, BPMN) represent diagrams, and how well can each express the icon set from [DRAKON icon set in drakonwidget](01-drakon-icon-set-in-drakonwidget.md), including optional coordinates and per-node content? Assess each for tree vs graph shape, standardisation, tooling support, and ease of use in other tools.

## Answer

All five formats store a **graph**. None stores a flowchart as a pure tree.

### drakonwidget JSON

- Typed-slot graph: `one` = down, `two` = right/next, `side` = duration.
- Grammar is enforced only by editor code.
- No layout section. Free icons are positioned.
- Per-icon fields: `content` + `secondary`, `link`, `style`. Text format is set for the whole Diagram.
- References to other Diagrams are by name, not id.
- Expresses the full baseline.

### drakon.tech `.drakon`

- A documented subset of drakonwidget's format.
- One file per Diagram, and the file name is the Diagram name. Folders are modules, `class X` folders are classes, and a `.dtproj` file describes the project.
- Adds `keywords` (code-generation flags) and the type ids `sinput`/`soutput`. These are the same concepts drakonwidget calls `simpleinput`/`simpleoutput`, so an importer must map them.
- Its toolchain (drakongen `toTree`) derives a nested yes/no/loop **tree** from the graph.
  - That conversion acts as a Grammar validator: it fails on unreferenced branches, bad loop exits, and empty non-last cases.
  - The tree is lossy: it drops which question exit is drawn down and the case order, and keeps no layout.

### Mermaid flowchart

- The text language is the canonical form. There is no public flowchart AST: the grammar is still Jison, and `@mermaid-js/parser` excludes flowchart.
- The internal model (FlowDB) is a graph of vertices, edges and nested subgraphs.
- No exit identity, no Grammar, no coordinates.
- One label per node, plus a fixed set of YAML metadata keys.
- Links are URLs only.
- Lossy for DRAKON. It is a good export target.

### JSON Graph Format v2.1

- A generic graph schema: a node has only `label` and `metadata`; an edge has `source`, `target` and `relation`.
- No nesting, no layout, no Grammar, no references between graphs.
- Every DRAKON concept would live in untyped metadata.
- A small community proposal.

### BPMN 2.0.2 (ISO/IEC 19510)

- A flow graph (`sequenceFlow` source/target) inside a containment tree.
- Grammar lives in the spec text and in linters (`bpmnlint`). The XSD only checks types.
- **Optional, separate, id-linked layout**: `BPMNDiagram` has `minOccurs=0`, using Bounds and waypoints.
- **Standard id-based references to other Diagrams**: `callActivity@calledElement`, plus `import`.
- Has `extensionElements` for custom data.
- No standard JSON form. bpmn-moddle is a JS object model that still writes XML.
- Good fit for DRAKON semantics, poor fit for DRAKON form.

### Inputs for ticket 03

These inform the decision; they do not make it.

- Graph storage plus a validator is the norm. drakonwidget, drakon.tech and BPMN all work this way.
- A tree view exists only as a derived, validating, lossy projection.
- A tree Model would have to add back: exit orientation, merge points, arrow loops, Address jumps, and case order.
- Import from drakonwidget is close to 1:1 into a graph Model. Into a tree Model it would need a structuring pass that can reject real Diagrams.
- BPMN's DI is a precedent for the map's optional coordinates section and for references by ID.
- No off-the-shelf JSON Schema fits, so the Schema will be bespoke.

Context: full findings with citations are in `/home/dev/projects/drakonwidget-research-formats/research/diagram-formats.md` on branch `research/diagram-formats` (commit 900ff7d, not pushed).
