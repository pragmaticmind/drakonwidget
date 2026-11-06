# Text view syntax mock-ups

Type: prototype
Status: resolved
Blocked by: 05

## Question

What does the chosen Text view syntax look like on realistic Diagrams (a primitive, a silhouette with several branches, nested questions, a loop, an insertion), and does it read well enough to author by hand?

## Answer

Resolved by prototype, 2026-11-01. Yes, the syntax reads well enough to author by hand, with the amendments below. Six real Diagrams from `dtsrc/` (`isUrl`, `getEarRole`, `copyFieldsOrDefault`, `unlinkArrow`, `debounce`, `hitBox`) were written by hand and then parsed by the live Text view editor. All parse without Problems. The flat and nested forms of `hitBox` give the same Model, and a mutation fuzz of 5000 edited texts never crashed the parser or produced a drawing without a Problem. Code-heavy Icon text gives long lines, which is acceptable because the audience writes short Icon text.

Amendments, recorded in the [rejoins and one-jump addenda](05-text-view-syntax-direction.md):

1. **One jump keyword**: `goto @name` replaces `join`, and `repeat … again` is not added (points 21 to 26).
2. **Guard shorthand** for chains of guard questions (point 28).
3. **`input` and `output` keywords** (point 29).
4. **End is implicit only at the bottom of the last branch** (point 30).
5. **Keywords are whole words**, and a quoted line is literal text (point 31).
6. **Params stay `\n`-separated**, with no comma list (point 32).

Prototypes: `prototypes/text-syntax/` on branch `prototype/text-syntax-mockups` (hand-converted examples) and `prototypes/text-view-editor/` on branch `prototype/text-view-syntax` (live editor).

## Comments

### 2026-11-01: one jump keyword (decided by the user, replaces part of ticket 05)

- `goto <branch>` switches branch (an address Icon). `goto @name` jumps to the line marked `@name` in the same branch. The `@` keeps branch and label names apart.
- `join` and `repeat … again` are dropped; `loop` stays as the only block loop.
- A `goto @name` that goes **down** in the drawing is a shared join. One that goes **up** is an arrow loop. Up or down is decided from the drawing (a jump that closes a cycle), not from line order, so `getEarRole` stays a join.
- An upward `goto @name` must be the last line of a question's side exit: from the down exit DRAKON cannot draw it, and anywhere else the loop has no way out. A `goto @name` to another branch is an error (use `goto <branch>`).
- Prototype: `prototypes/text-view-editor/` on branch `prototype/text-view-syntax` (walkthroughs "goto @label: join" and "goto @label: loop").

### 2026-11-03: default next branch and reachability warnings (decided by the user)

- A path reaching the bottom of a branch continues to the next branch in text order, including empty branches and outcomes without an explicit jump. Explicit jumps take precedence. Only the final branch defaults to End.
- Reachability starts at the first branch and follows every possible explicit or default transition. Disconnected cycles are unreachable too.
- Emit one non-blocking warning on each unreachable branch's declaration: “Branch ‘B’ is never reached from the first branch.” Use amber, click to select the line, and keep the branch in the Model and on the Canvas. Do not repeat this warning on its Icons.
- Regression seams: `DrakonText.parse` and `DrakonText.toDrakonwidget`, plus a browser check for warning styling, navigation, and continued drawing.

### 2026-11-04: optional wrapper and inline question jumps (approved by the user)

- A Diagram may start directly with `primitive <name>` or `silhouette <name>` at the top level. The original `drakon` wrapper remains valid. Both forms still allow only one Diagram per text.
- A single-jump outcome may use `yes goto <branch>` / `no goto <branch>` or the corresponding `goto @label` form. It has the same Model, exit ordering, guard behaviour, and jump validation as an indented outcome.
- Inline outcomes cannot also have indented steps. Other inline statements remain invalid; use the existing block form for several steps.
- Existing valid walkthroughs are tested for equivalent Models with wrapper-free headers and inline jumps. Browser coverage checks the concise walkthrough, drawing, and warning navigation at the shortened source line.

### 2026-11-04: single-entry loop bodies (requested by the user)

- A `goto` may not jump from outside a loop into its body. The restriction also applies to an outer loop jumping into an inner body, and jumps between sibling bodies.
- A label directly above the `loop` line still leads through the normal entry point. Same-loop joins and arrow loops retain their existing validation.
- Jumping out is allowed, including multiple exits, exits into an enclosing loop, exits leaving several loops, and branch jumps.
- The supplied “Mistakes” example must produce one error at its incoming inline `goto` on line 5, not at the outward jump on line 12.
- Browser verification exposed a separate renderer limitation: drakonwidget throws `Cannot read properties of undefined (reading 'tail')` for the valid multiple-exit walkthrough. Outward jumps stay accepted in the Text view and Model; Canvas support remains follow-up work.
