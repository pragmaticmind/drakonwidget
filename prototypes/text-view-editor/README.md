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
- Guard shorthand: a question that lists a single `yes` or `no` block ending in `goto` puts that block on the side, and the following lines continue downwards.
- `input`, `output`, `shelf <who>: <what>`, `insert <text> -> <id>`, `note:`, the `[duration]` suffix and `"literal"` lines are supported.
- The old keywords `join`, `repeat` and `again` are flagged as Problems.

## Findings so far

- **The guard shorthand matches the full form.** The flat `hitBox` produces the same Model as the version nested four levels deep. A loop-back written only in the `no` block also produces the same Model as writing both `yes` and `no` blocks.
- **Up or down must be read from the drawing.** `getEarRole` has its label on an earlier line, yet it draws as a join.
- **drakonwidget expects the arrow loop at the top.** Its `arrow-loop` item sits at the top of the loop: both the line coming in from above and the loop-back point at it.
- **No End is fine.** drakonwidget draws a Diagram with no End Icon (the `debounce` state machine) without trouble.
- **drakonwidget fails on Models with gaps.** When the text has Problems, drakonwidget throws internal errors. The Canvas view therefore shows the first Problem, with its suggested fix, instead.
