# Text view syntax mock-ups

Type: prototype
Status: claimed
Blocked by: 05

## Question

What does the chosen Text view syntax look like on realistic Diagrams (a primitive, a silhouette with several branches, nested questions, a loop, an insertion), and does it read well enough to author by hand?

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
