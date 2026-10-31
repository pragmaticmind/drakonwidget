# Prototype: Text view syntax on real Diagrams

Throwaway. This is the **Text view syntax mock-ups** ticket on the Drakon Editor wayfinder map. It tests the syntax decided in **Text view syntax direction** (and its rejoins addendum) against real DRAKON Diagrams from this repo's `dtsrc/` corpus.

The Diagrams were converted **by hand**. There is no parser yet. To check a conversion, print the source graph and compare it with the example:

```sh
python3 prototypes/text-syntax/dump.py "dtsrc/drakon_canvas/Utils/hitBox.drakon"
```

When reading the dump:
- `one` is the down exit and `two` is the right exit.
- On a question, `flag1: 1` means *yes* is drawn down.
- A link pointing at a `branch` item is an address (`goto`).

## Examples

- **`01-isUrl.txt`** (source `dtsrc/drakon_canvas/TextBlock/isUrl.drakon`). Tests: nested questions, a structured rejoin, and a **shared join** into `return false`.
- **`02-getEarRole.txt`** (source `dtsrc/drakon_canvas/class DrakonCanvas/Free/Ears/getEarRole.drakon`). Tests: `select`, an empty default case, and two cases sharing one Icon.
- **`03-copyFieldsOrDefault.txt`** (source `dtsrc/drakon_canvas/Utils/copyFieldsOrDefault.drakon`). Tests: a FOR `loop` with a question inside, and multi-line params.
- **`04-unlinkArrow.txt`** (source `dtsrc/drakon_canvas/class DrakonCanvas/Private/Deletion/Traverse items/unlinkArrow.drakon`). Tests: a silhouette, an **arrow loop** with *no* drawn down, `goto`, and an empty last branch.
- **`05-debounce.txt`** (source `dtsrc/utils/debounce.drakon`). Tests: a state machine with no End, a simple input Icon, `goto` from inside a `case`, and a branch that jumps to itself.
- **`06-hitBox.txt`** and **`06-hitBox.guard-form.txt`** (source `dtsrc/drakon_canvas/Utils/hitBox.drakon`). Tests: a chain of four guard questions sharing one *no* target, written in full and in the proposed shorthand.

## What worked

- **Rejoin by placement**: every structured rejoin in these Diagrams was expressible by nesting alone. Examples: `isUrl`'s inner questions rejoining before `try …`, and `copyFieldsOrDefault`'s *no* block rejoining before `dst[field] = value`.
- **`@name` / `join name`**: it covered every shared target (`isUrl`, `getEarRole`, `hitBox`) without duplicating any Icon.
- **First-listed exit drawn down**: `unlinkArrow`'s question is drawn with *no* going down (`flag1: 0`). Listing `no` first keeps that in the text.
- **`goto` everywhere**: `goto` works at the end of a branch, inside a `case`, and to the branch's own start (`debounce`).

## Findings, with proposed amendments

1. **A join can point to an earlier line yet still go down in the drawing.** In `getEarRole`, case "down" joins the Icon under case "up". In the text that is an *earlier* line; in the drawing it is lower and to the left. **Amend**: replace "a join goes to a later line" with "a join must not go upward in the drawing". A label may be defined before or after its `join`, and the Grammar validator checks the drawing.
2. **Guard chains nest deeply.** `hitBox` in full form needs four levels of indentation, while DRAKON draws it flat. **Propose a guard shorthand**: if a question lists only one exit block, and that block ends in `join` or `goto` (so it never falls through), the other exit is the following lines and is drawn down. See `06-hitBox.guard-form.txt`.
3. **`repeat … until` does not say which exit loops, and loses the orientation.** In `unlinkArrow`, *yes* loops back and *no* goes down. **Amend**: a `repeat` block, plus the keyword `again` inside the exit that loops back to the top of the `repeat`. Orientation follows the first-listed rule as usual.
4. **State machines never reach End.** In `debounce`, every path ends in `goto`. **Clarify**: End is implicit only where flow falls off the bottom of the last branch. A last branch whose paths all end in `goto` has no End.
5. **Input and output Icons have no keyword yet.** **Propose**:
   - `input <text>` and `output <text>` for the simple forms;
   - `input <who>: <what>` and `output <who>: <what>` for the two-part forms, like `shelf`.

   The import from drakon.tech maps `sinput` and `soutput` to these.
6. **Keyword collisions.** `action(msg)` in `debounce` starts with the word `action`. **Clarify**: a keyword counts only as a whole word followed by a space or the end of the line. Otherwise, quote the text.
7. **Params are line lists in DrakonTech** (`dst\nsrc\nfields\ndefaultValue`). With the one-line rule they become `(dst\nsrc\nfields\ndefaultValue)`, which is lossless but noisy. **Option**: allow `(dst, src, fields, defaultValue)` as a list form. Open question.
8. **Code-heavy Icons produce long lines** (`isUrl`, `unlinkArrow`, `debounce`). That is acceptable for the main audience, business analysts, whose Icon text is short. Code Diagrams stay correct, just less pleasant to read.
9. **An empty `case`** (the default case) is written as a bare `case`. Only the rightmost case may be empty, as decided.
10. **DrakonTech `keywords`** (`function`, `export`, …) have no place in the text. The import keeps them in the Diagram's `meta`. That is a note for the **drakonwidget import mapping** ticket.

## For you to react to

1. Use "not upward in the drawing" as the join rule (finding 1)?
2. Add the guard shorthand (finding 2)?
3. Use `repeat` plus `again` instead of `repeat … until` (finding 3)?
4. Use the keywords `input` and `output` (finding 5)?
5. Allow comma-separated params (finding 7)?
