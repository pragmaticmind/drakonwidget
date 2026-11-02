# Coordinates section semantics

Type: grilling
Status: claimed
Blocked by:

## Question

How does the optional coordinates section coexist with automatic layout and the Grammar: can manually placed positions violate the Grammar, what happens to stored coordinates when the structure changes, and is it all-or-nothing per Diagram or partial per node?

## Context

- Ticket 03 stores the Model as a graph and says layout is an optional, separate section keyed by Icon id (BPMN DI pattern). The prototype Schema (`prototypes/model-format/schema/own.schema.json` on `prototype/model-format-own-vs-jgf`) has `layout.icons[id] = {x, y}`, filled in for only part of the sample Diagram. Nothing yet says what those numbers mean.
- In DRAKON the drawing is fully determined by the structure: a vertical main line, branches as columns in array order, and no crossing lines (ticket 01 Grammar, ticket 03 addendum). The only free choices are sizes and spacing.
- Ticket 05 point 12: the Text view hides layout but keeps it when the text is edited.
- `group-duration` is the one free Icon in the baseline that is not part of the flow. Ticket 03 point 9 left it out until this ticket.
- Not checked: whether drakonwidget stores positions for flow Icons on `type:"drakon"` Diagrams, or only for free-type Diagrams. The import mapping ticket (07) has to answer that.

## Comments

### 2026-11-01: grilling in progress

Questions in dependency order, each with the agent's recommendation. Status stays `claimed` until they are answered.

1. **What are coordinates for?** Since structure fixes the drawing, a manually moved flow Icon would break the Grammar. Options: (a) flow Icons never have coordinates, they are only for free Icons; (b) coordinates are a layout cache for flow Icons; (c) coordinates are nudges (extra spacing, branch width). **Recommend (a)** for the first version. The Canvas view's layout is always derived from the structure. A viewer that needs a static drawing without running layout is the "Model to SVG renderer" fog item and can bring a cache (b) later.
2. **Which Icons may have coordinates?** Recommend: only free Icons. Today that is `group-duration` and nothing else. The Schema rejects `layout` entries for flow Icons, so the Grammar cannot be violated through coordinates.
3. **Absolute or anchored?** Absolute x and y for a free Icon drift away from the flow Icons they annotate whenever the structure changes. Recommend: a free Icon is anchored to a flow Icon id plus an offset `{anchor, dx, dy}`, and does not use absolute x and y.
4. **When the structure changes.** If the anchor Icon is deleted, recommend the free Icon is deleted with it (same undo step), because it has nothing left to annotate. A dangling anchor in imported or hand-edited JSON is an `error` diagnostic.
5. **All-or-nothing or partial?** Recommend partial per Icon, since the section is keyed by id. A free Icon without a layout entry is placed automatically next to its anchor. An entry whose id is not in the Diagram is dropped on the next committed edit and reported as a `hint`.
6. **Existing Schema field.** Recommend replacing the prototype's `layout.icons[id] = {x, y}` with the anchored form in 3, and renaming the section so it does not suggest a layout of the whole Diagram. This changes the "Free icons" line in ticket 03 point 9 and the map note "coordinates are an optional section, so both manual and automatic layout are supported", which would become "automatic layout only, anchored free Icons".
7. **Text view.** Free Icons need a text form, or they are invisible in the Text view. Recommend `duration` as a suffix on the line of its anchor (ticket 05 already has the `[duration]` suffix), so `group-duration` is the only free Icon left over.

Question 1 decides the rest. If you want manual layout of flow Icons, say so and I will rework 2 to 6.

### 2026-11-02: use cases from the user (answers question 1, reworks 2 to 7)

Decided by the user: flow Icons **can** carry layout information, in a variation of coordinates, for two use cases:

- **A. Align Icons across branches.** Icons on different branches are drawn at the same level because the alignment carries meaning (for example, steps that happen at the same time, or a hand-over).
- **B. Draw compactly.** A Diagram can be drawn more compact when branches overlap, for example a wide action fits into the empty space beside a shorter neighbouring branch.

This replaces the earlier recommendation (a) of question 1. The questions below are the reworked ones; the earlier questions 2 and 4 (flow Icons never have coordinates) are withdrawn.

Observation that shapes the questions: branches are independent columns that touch only through `goto` addresses, and the drawing has no lines between columns. So neither use case can create a crossing line. A is a *meaning* (a relation between Icons). B is a *drawing choice* (spacing), which the structure does not need.

1. **Representation of A.** Options: (a) alignment groups, named sets of Icons that share one level; (b) a logical row number per Icon; (c) pixel y. **Recommend (a).** A group survives inserting or deleting Icons without renumbering, and the group name can carry the meaning ("step 3", "hand-over"). Pixel coordinates (c) break whenever text wraps or an Icon is added.
2. **What aligned means.** Recommend: the vertical centres of the member Icons are on one horizontal line. Shorter branches get white space above the member to make room. Alignment never reorders flow.
3. **When an alignment group is valid.** Recommend: a group has at most one Icon per branch and spans at least two branches (alignment inside one branch says nothing the flow order does not). The groups must be consistent with each branch's flow order: if group G1 comes before G2 in one branch and after it in another, that is a cycle and an `error` diagnostic that names both groups and the branches.
4. **Representation of B.** Options: (a) a stored per-branch x offset; (b) one Diagram-level switch, and the layout engine packs automatically; (c) per-Icon "may overlap" marks. **Recommend (b)**: a Diagram-level `compact` flag, default off, because the regular column look is the DRAKON default. When on, the engine packs deterministically from the structure and the alignment groups. A wide Icon may extend over a neighbour's empty rows and never over anything drawn. Branch order stays left to right. Alignment groups fix the rows first, packing decides the horizontal spacing after.
5. **Schema.** Recommend replacing the prototype's `layout.icons[id] = {x, y}` with `layout: {compact?: boolean, alignments?: [{id, label?, icons: [iconId, ...]}]}`. No pixel numbers are stored. It stays optional, keyed by Icon id, and the Model stays valid without it (a viewer that ignores layout still draws a correct Diagram).
6. **When the structure changes.** Deleting an Icon removes it from its group, and a group left with fewer than two Icons is removed. An edit that would make a group invalid (moving a member into a branch that already has one, or creating an order cycle) drops that Icon from the group and tells the author with a `hint`, instead of refusing the edit. Hand-edited or imported JSON that is invalid gets an `error`.
7. **Free Icons.** `group-duration` still needs a decision. Recommend it stays out of the first version, since A and B no longer need free Icons, and that the earlier anchored-offset idea waits until a use case needs it. Confirm or reverse.
8. **Text view.** Without a text form, alignments are invisible in the Text view (05 point 12 keeps them, hidden). Recommend a text form is needed, because the alignment carries meaning. Recommend deciding the spelling in a mock-up, like ticket 06, because Icon text may itself contain `{`, `[` and `~` (code-heavy Icons), so a suffix needs the same whole-word and quoting rules as the other suffixes. `compact` can be a header option on the `drakon` line.
9. **Layout engine.** A and B constrain the automatic layout algorithm (fog item). Recommend recording both as inputs to that ticket rather than designing the algorithm here. drakonwidget has neither feature as far as I have seen, so there is nothing to import; I have not checked its layout code, so ticket 07 should confirm.

If these are accepted, 04 resolves with questions 1 to 9 as written, and a follow-up prototype ticket covers the Text view spelling.
