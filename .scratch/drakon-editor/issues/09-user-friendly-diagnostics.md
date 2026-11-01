# User-friendly diagnostics

Type: grilling
Status: open
Blocked by:

## Question

How should Text view diagnostics help a business analyst fix a mistake, not just report it? For example, `goto Afsluit` should suggest the closest branch names ("Did you mean: Afsluiten?"), and the same goes for `goto @label` targets and misspelled keywords (`questoin`). What rules decide when a suggestion is shown (edit distance, case and accent folding, how many suggestions), and should the editor offer a one-click fix?

## Context

- The Text view prototype (`prototypes/text-view-editor/`, branch `prototype/text-view-syntax`) currently says only "There is no branch called “Afsluit”." See the "Silhouette and goto" walkthrough, step 3.
- Other candidates for suggestions: an unknown label in `goto @label`, a keyword typo read silently as an action, `yes`/`no` outside a question, and indentation that is off by one space.
- First worked example (prototype, 2026-11-01): a loop-back `goto @name` outside a question names the label, the target step and its line, explains that nothing decides when to stop, and shows the three lines to type instead. When the Canvas view cannot draw the text, it shows the first diagnostic and its suggestion instead of drakonwidget's internal error. See [Text view syntax direction](05-text-view-syntax-direction.md) point 27.
- Relates to the fog items "Grammar validation and error reporting" and the `onDiagnostics` shape in [Embedding API shape](08-embedding-api-shape.md).

## Comments

### 2026-11-01: grilling in progress

Status stays `open` until the remaining questions are answered.

- **Decided (by the user): the editor offers a one-click fix.** A diagnostic may carry fixes, each a text edit the author applies with one click. Nothing is ever applied automatically.
- **Still to decide**, each with the agent's recommendation:
  1. When to suggest: only for names checked against a known set (branches after `goto`, labels after `goto @`, keywords). Case and accent folded, Damerau-Levenshtein distance at most `max(1, floor(length / 4))`, and a prefix always matches.
  2. How many: the closest if it is clearly best, otherwise at most 3, never a full list, nothing when none is near.
  3. Keyword typos (`questoin Is dat zo?`): a hint, not a Problem, since the line is valid as an action. Only when the first word is within distance 1 to 2 of a keyword and more words follow.
  4. One-click button: shown only when there is exactly one fix. With several, the author chooses from a list.
  5. `onDiagnostics` item shape: `{severity, code, message, range, fixes?}`, with `fixes` as `{label, edit}` and `edit` a ranged text replacement. `code` is a stable id such as `unknown-branch`, so Hosts can translate.
  6. Severity: two levels, `error` (no Model, nothing drawn) and `hint` (valid but probably a mistake).
  7. Messages that have a suggestion name the author's own label, text and line, say why, and show the lines to type (point 27 of ticket 05).
