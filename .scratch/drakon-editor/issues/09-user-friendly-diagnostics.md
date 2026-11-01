# User-friendly diagnostics

Type: grilling
Status: open
Blocked by: 06

## Question

How should Text view diagnostics help a business analyst fix a mistake, not just report it? For example, `goto Afsluit` should suggest the closest branch names ("Did you mean: Afsluiten?"), and the same goes for `goto @label` targets and misspelled keywords (`questoin`). What rules decide when a suggestion is shown (edit distance, case and accent folding, how many suggestions), and should the editor offer a one-click fix?

## Context

- The Text view prototype (`prototypes/text-view-editor/`, branch `prototype/text-view-syntax`) currently says only "There is no branch called “Afsluit”." See the "Silhouette and goto" walkthrough, step 3.
- Other candidates for suggestions: an unknown label in `goto @label`, a keyword typo read silently as an action, `yes`/`no` outside a question, and indentation that is off by one space.
- First worked example (prototype, 2026-11-01): a loop-back `goto @name` outside a question names the label, the target step and its line, explains that nothing decides when to stop, and shows the three lines to type instead. When the Canvas view cannot draw the text, it shows the first diagnostic and its suggestion instead of drakonwidget's internal error. See [Text view syntax direction](05-text-view-syntax-direction.md) point 27.
- Relates to the fog items "Grammar validation and error reporting" and the `onDiagnostics` shape in [Embedding API shape](08-embedding-api-shape.md).
