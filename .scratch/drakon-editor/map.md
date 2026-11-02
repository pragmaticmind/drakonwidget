# Drakon Editor

Label: wayfinder:map

## Destination

An implementation-ready spec for a new standalone TypeScript DRAKON editor: one JSON Model as the source of truth, edited both ways by a Text view and a Canvas view, with the Grammar always enforced. drakonwidget is only a reference and an import source. The spec covers the data model, the editing model, the architecture, and a generic Host embedding interface.

## Notes

- Domain: DRAKON diagrams for business and human/digital workflows. Use the vocabulary in `GLOSSARY.md` (Diagram, Schema, Model, Text view, Canvas view, Grammar, Host).
- Every session consults the `grilling` and `domain-modeling` skills; research tickets use the `research` skill.
- Standing preferences: TypeScript; framework-free core; SVG rendering; shipped as one embeddable package (web component or `mount(el, options)`).
- The Model stores structure and content; coordinates are an optional section, so both manual and automatic layout are supported.
- One Diagram per Model; insertions refer to other Diagrams by ID.
- Icon baseline: parity with drakonwidget's icon set.
- Tracker: local markdown, see `docs/agents/issue-tracker.md`.

## Decisions so far

<!-- one line per resolved ticket: [title](issues/NN-slug.md): gist -->
- [DRAKON icon set in drakonwidget](issues/01-drakon-icon-set-in-drakonwidget.md): 27 stored DRAKON item types plus virtual Address/junction. The graph uses `one` (down) / `two` (right) / `side` (duration) links. Constructs are primitive/silhouette (branch count), question (`flag1`), select+case chain, loopbegin/loopend nesting, arrow-loop back-link, and parbegin/parend. Findings: worktree `drakonwidget-research-icons`, branch `research/drakon-icon-set`.
- [Embedding API shape](issues/08-embedding-api-shape.md): `mount(el, options)` plus a `<drakon-editor>` wrapper. Model in via option/`setModel` (strict Schema check), out via `getModel()` copy and full-Model `onChange` per committed edit. `onDiagnostics`, a view mode (canvas/text/split), `readOnly`, and `onInsertionActivate(diagramId)`. Ships as ESM + IIFE.
- [Survey of existing diagram data formats](issues/02-survey-of-existing-diagram-data-formats.md): all five formats store graphs. The only tree is drakongen's derived, validating, lossy projection. BPMN DI is the precedent for an optional, id-linked layout section and for references by ID. drakon.tech's `sinput`/`soutput` map to `simpleinput`/`simpleoutput`. No off-the-shelf Schema fits. Findings: worktree `drakonwidget-research-formats`, branch `research/diagram-formats`.
- [Model shape: tree or graph](issues/03-model-shape-tree-or-graph.md): graph of Icons with named exits (`next`/`yes`/`no`/`down`/`cases`/`end`/`branch`), own versioned Schema (not JSON Graph Format), derived tree for Text view/layout/validation. Explicit address Icons and loop pairing, ordered `branches[{id,name,first}]`, Diagram `id` + `schemaVersion`, per-Diagram `textFormat`, free `meta`. Prototype: PR #1.
- [Text view syntax direction](issues/05-text-view-syntax-direction.md): indented outline with header `drakon` and then `silhouette`/`primitive <name> (<params>)`. One line per Icon (`\n` for line breaks); a plain line is an action. `question` with `yes`/`no` blocks (first-listed exit drawn down), `select`/`case`, `goto` addresses, implicit End in the last branch. English, case-insensitive keywords. IDs/meta/layout hidden but kept. Raw JSON "Source" tab.
- Addendum to [Text view syntax direction](issues/05-text-view-syntax-direction.md) and [Model shape: tree or graph](issues/03-model-shape-tree-or-graph.md): rejoins follow placement (directly after the blocks, skipped steps nested in the main-line block). Shared joins use text-only `@name` / `join name` (downward, same branch, no crossings). The derived structure is a tree plus downward joins.
- Addendum to [Text view syntax direction](issues/05-text-view-syntax-direction.md) (2026-11-01, from the [Text view syntax mock-ups](issues/06-text-view-syntax-mock-ups.md) prototype): one jump keyword. `goto <branch>` is an address; `goto @name` is a join when the target is lower in the drawing and an arrow loop when it is higher. `join` and `repeat … again` are dropped; `loop` stays. A loop-back must end a question's side exit. Diagnostics name the author's own label, text and line, and suggest a fix where possible.
- [Text view syntax mock-ups](issues/06-text-view-syntax-mock-ups.md): six real Diagrams from `dtsrc/` parse without Problems in the live Text view editor. Addendum to [Text view syntax direction](issues/05-text-view-syntax-direction.md): guard shorthand for chains of guard questions, `input`/`output` keywords (`<who>: <what>` for the two-part forms), End implicit only at the bottom of the last branch, keywords are whole words, params stay `\n`-separated. Prototypes: `prototype/text-syntax-mockups`, `prototype/text-view-syntax`.
- [User-friendly diagnostics](issues/09-user-friendly-diagnostics.md): suggestions only against known sets (branches, `@labels`, keywords), case and accent folded, distance at most `max(1, floor(length / 4))` and prefixes match, at most 3 and only when near. Keyword typos are a `hint`. One-click fix, shown only when there is exactly one. `onDiagnostics` item `{severity, code, message, range, fixes?}` with stable `code`s, severity `error` or `hint`. Messages name the author's own label, text and line.
- [Coordinates section semantics](issues/04-coordinates-section-semantics.md): the Model stores relations, not pixels: `layout: {compact?, alignments?: [{id, label?, icons[]}]}`. Alignment groups put member Icons on different branches at one level (vertical centres). A group of one Icon is inert; groups on two or more branches are active, and conflicting orders are an `error`. `compact` (default off) lets the layout engine pack branches so a wide Icon can use a neighbour's empty rows. Guides and markers in the Canvas view, `options.showAlignments`. `group-duration` stays out of the first version. Text spelling is [ticket 10](issues/10-alignment-text-syntax-mock-ups.md).

## Not yet specified

- Editing model: canvas interactions, selection, drag and drop, in-session undo/redo, and which of these the Editor handle exposes to the Host (undo/redo, zoom, focus).
- Text view ↔ Model sync: invalid text mid-typing, preserving text formatting and comments when the Canvas view edits.
- Grammar validation and error reporting.
- Automatic layout algorithm, including how it honours alignment groups and `compact`.
- Node metadata extension (owner, role, system, SLA).
- Theming and styling.
- Export plugins (SVG, PNG, Mermaid, BPMN), including a static Model→SVG renderer for viewer-only Hosts.
- Patch-style change events for Hosts that need incremental updates.
- Multi-Diagram projects.
- Icons beyond drakonwidget parity.
- Model validity as JSON Graph Format (parked; revisit if a consumer needs it).
- Per-Icon text format overrides.
- Free-floating Icons such as `group-duration` (left out of the first version by Coordinates section semantics).
- Localized keywords for the Text view.

## Out of scope

- Confluence and Jira integration: deferred to a later effort; only the generic Host embedding interface is in scope.
- New icon kinds via plugins: not needed.
- Real-time collaboration, storage backends, persisted undo history: the Host owns storage.
- Export back to drakonwidget format: import is one-way.
- Building the editor: happens after this map.
