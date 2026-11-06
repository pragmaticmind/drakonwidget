# Prototype: live Text view editor

Throwaway. This is part of the **Text view syntax mock-ups** ticket (`.scratch/drakon-editor/issues/06-text-view-syntax-mock-ups.md`) on the Drakon Editor wayfinder map.

It answers this question: can a process owner write a Diagram as an indented outline and get exactly the drawing they meant?

## Run it

Open `index.html` in a browser by double-clicking it. There is no server and no build. It loads `../../libs/drakonwidget.js`.

To open a walkthrough step directly, add `#s=<tab>&k=<step>` to the URL. For example, `index.html#s=4&k=4` opens the loop-back mistake.

## How it works

1. **Text → Model.** `DrakonText.parse` turns the text into a Model in the ticket 03 shape and collects diagnostics. It lives in the `<script id="logic">` block, which is pure: no DOM access.
2. **Model → drakonwidget.** `DrakonText.toDrakonwidget` converts the Model into drakonwidget items.
3. **Draw.** `libs/drakonwidget.js` draws the result, read-only.

The page around the logic block is a thin shell:
- the editor
- buttons that insert snippets
- a panel showing what the text says
- the Problems list
- the Model and drakonwidget JSON
- the guided walkthroughs

## Syntax tested

The syntax is ticket 05 plus its 2026-11-01 addendum.

- `goto <branch>` switches branch.
- `goto @name` jumps to the line marked `@name`. When the target is lower in the drawing it is a join; when it is higher it is an arrow loop.
- `loop` is the only block loop.
- A `goto @label` cannot enter a loop body from outside that loop, including from an outer or sibling loop. Enter through the `loop` line instead (a label immediately above that line is valid). Jumps within the same loop keep the existing join/arrow-loop rules. Jumps out are allowed, including multiple exits to different labels, exits into an enclosing loop, and jumps leaving several loops or switching branch.
- Guard shorthand: a question that lists a single `yes` or `no` block ending in `goto` puts that block on the side, and the following lines continue downwards.
- `input`, `output`, `shelf <who>: <what>`, `insert <text> -> <id>`, `note:`, the `[duration]` suffix and `"literal"` lines are supported.
- The old keywords `join`, `repeat` and `again` are flagged as Problems.

## Findings so far

- **The guard shorthand matches the full form.** The flat `hitBox` produces the same Model as the version nested four levels deep. A loop-back written only in the `no` block also produces the same Model as writing both `yes` and `no` blocks.
- **Up or down must be read from the drawing.** `getEarRole` has its label on an earlier line, yet it draws as a join.
- **drakonwidget expects the arrow loop at the top.** Its `arrow-loop` item sits at the top of the loop: both the line coming in from above and the loop-back point at it.
- **No End is fine.** drakonwidget draws a Diagram with no End Icon (the `debounce` state machine) without trouble.
- **drakonwidget fails on Models with gaps.** When the text has Problems, drakonwidget throws internal errors. The Canvas view therefore shows the first Problem, with its suggested fix, instead.
- **Warnings are not drawing errors.** Unreachable branches stay visible. If drawing fails, the Canvas error panel uses an error diagnostic, never an unreachable-branch warning.
- **Block-loop early exits expose a Canvas limitation.** They are valid in the Text view and Model, but drakonwidget currently throws an internal `tail` error on the multiple-exit walkthrough. This is a renderer limitation, not a reason to reject outward jumps. Loop-boundary tests check parser diagnostics and Model connections; browser checks verify error navigation and valid Model display without claiming that early-exit diagrams render.

## Regression tests

Run `node --test prototypes/text-view-editor/text-view.test.cjs` from the repository root. Uses Node's built-in test runner, with no dependencies.

The suite exercises `DrakonText.parse` and `DrakonText.toDrakonwidget`: optional wrappers, inline question jumps and their diagnostics, compatibility with indented outcomes, default transitions, explicit jumps, empty branches, disconnected and reachable cycles, partial question/case outcomes, loop exits, and the guided walkthroughs.

Run `node --test prototypes/text-view-editor/*.test.cjs` to include the headless browser regression. It requires `google-chrome` on PATH, or `CHROME_BIN` pointing to a Chrome/Chromium executable. It checks amber styling, click-to-line navigation, warning removal after editing, and continued Canvas rendering with all branches visible. Its temporary browser profile is removed afterwards.
