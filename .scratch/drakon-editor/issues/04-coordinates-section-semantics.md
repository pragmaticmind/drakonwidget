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
