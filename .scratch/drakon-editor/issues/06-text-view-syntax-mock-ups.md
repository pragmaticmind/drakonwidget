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
