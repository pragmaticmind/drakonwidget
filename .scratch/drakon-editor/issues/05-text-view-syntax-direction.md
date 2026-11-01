# Text view syntax direction

Type: grilling
Status: resolved
Blocked by: 02, 03

## Question

What kind of syntax should the Text view use: a custom Mermaid-like DSL, the JSON/JSON5 Model shown directly, YAML, or DRAKON-style structured pseudo-code?

## Answer

Resolved by grilling, merging the agent's proposal with the user's own example.

1. **Family**: an indented outline, which is the derived tree written as text. Two-space indentation means nesting.
2. **Header**: the first line is `drakon` (diagram-type header, as in Mermaid), followed by `silhouette <name> (<params>)`, or `primitive <name> (<params>)` for a single-branch Diagram. The text in parentheses is the Diagram's `params`; a free description goes in `meta`.
3. **One line per Icon**: keyword and text share one line (`question Is een vraag?`). A multi-line text is written with `\n`, and `\\` is a literal backslash.
4. **Actions**: a line that does not start with a keyword is an action; the `action` keyword is optional.
5. **Questions**: `question <text>` with indented `yes` and `no` blocks. **The exit listed first is drawn down** (`down` in the Model). An empty block goes straight to the merge point.
6. **Select**: `select <text>` with indented `case <text>` blocks, in order. Only the rightmost case may be empty (otherwise a diagnostic).
7. **Merge**: after a `question` or `select`, the flow continues on the lines below its blocks.
8. **Branches**: `branch <name>` under the silhouette. Every branch except the last must end in `goto <branch>` (an address Icon). The last branch ends in End implicitly. Violations are diagnostics.
9. **Other constructs**: `loop <text>` (body indented, loop end where the indentation stops), `repeat` … `until <question>` (arrow loop), `shelf <who>: <what>`, `insert <text> -> <diagram-id>`, `note: <text>`, `[duration]` suffix, `"…"` for literal text that starts with a keyword. Exact spellings are for Text view syntax mock-ups to confirm.
10. **Audience**: business analysts and process owners, so plain-word keywords, few symbols, and case-insensitive keywords.
11. **Keywords**: English only. Icon text can be in any language. Localized keywords go in the fog.
12. **Coverage**: the text shows flow and text only. IDs, `meta` and layout are hidden but kept when the text is edited (matching details are in the Text view ↔ Model sync fog).
13. **Grammar by structure**: indentation makes most Grammar errors impossible to write; the remainder are reported through `onDiagnostics`.
14. **Not literal Mermaid**: Mermaid stays an export plugin.
15. **Raw JSON**: a secondary "Source" tab shows the Model as JSON, checked against the Schema.
### Addendum: rejoins (2026-10-31)

> Superseded by the 2026-11-01 addendum below: `join name` (points 18 and 19) is now written `goto @name`, and `repeat … until` (point 9) is replaced by `goto @name` back up.

16. **Rejoin directly**: a side flow rejoins the main line on the line directly below its question's (or select's) blocks.
17. **Rejoin further down**: steps a side flow skips are placed inside the first-listed (main-line) block. An empty block goes straight to the join point.
18. **Shared joins**: when side flows share an Icon, mark the point with `@name` and jump to it with `join name`. A join only goes downward (to a later line), within the same branch, and must be drawable without crossing lines; anything else is a diagnostic. Upward jumps happen only through `loop` or `repeat … until`.
19. **Case endings**: a `case` block falls through to the line after the `select`, ends with `goto <branch>`, or ends with `join <name>`.
20. **Labels are text-only**: `@name` labels are not stored in the Model. When text is generated from the Model, the label is derived from the target Icon's text (for example `@order-afwijzen`).

```text
question Klant bekend?
  yes
    question Krediet ok?
      yes
        Order bevestigen
      no
        join afwijzen
  no
    @afwijzen
    Order afwijzen
Order archiveren
```

Example:

```text
drakon
  silhouette "Claim afhandeling" (claim)
    branch Controle
      question Is een vraag?
        yes
          goto Keuze
        no
          goto Afsluiten
    branch Keuze
      select Welke van de drie
        case A
          Doe A
        case B
          Doe B
        case C
      goto Afsluiten
    branch Afsluiten
      Meld het resultaat\nper e-mail
```

### Addendum: one jump keyword (2026-11-01)

Decided while prototyping [Text view syntax mock-ups](06-text-view-syntax-mock-ups.md). Replaces `join name` (points 18 and 19) and the proposed `repeat … again`.

21. **`goto` is the only jump keyword.** `goto <branch>` switches branch and becomes an address Icon. `goto @name` jumps to the line marked `@name`. The `@` tells the two apart, so a branch and a label may share a name.
22. **Down is a join, up is a loop.** A `goto @name` whose target is further down in the drawing is a shared join. One whose target is further up is an arrow loop. Up or down is read from the drawing (a jump that closes a cycle), not from line order: a label on an earlier line can still be a join (`getEarRole`).
23. **`loop` is the only block loop.** `repeat … again` is not added; any other loop is `@name` above the first step and `goto @name` back to it.
24. **Where a loop-back may sit.** An upward `goto @name` must be the last line of the yes or no block that is drawn to the side. From the exit drawn downwards it cannot be drawn; on the main line or directly in a `case`, nothing decides when to stop.
25. **Same branch only.** `goto @name` to a label in another branch is a diagnostic; use `goto <branch>`.
26. **Unreachable lines.** Any line no path reaches (after a `goto`, or after a question whose exits all jump away) is a diagnostic and is not drawn.
27. **Diagnostics explain and suggest.** A diagnostic names the author's own label, step text and line number, says why it is a problem, and where possible gives the lines to type instead. Example for a loop-back without a question:

    > goto @call loops back to “Call the customer” (line 4) without a question. Nothing decides when to stop, so every step from there down to here would repeat forever. Let a question decide whether to go round again, and put the goto in its yes or no block:
    > `question Go round again?` / `  yes` / `    goto @call`

    The general rules for such messages are open in [User-friendly diagnostics](09-user-friendly-diagnostics.md).

```text
drakon
  primitive "Reach the customer"
    @call
    Call the customer
    question Did they answer?
      no
        Wait one hour [1 h]
        goto @call
    question Order complete?
      yes
        question Payment ok?
          yes
            Confirm the order
          no
            goto @reject
      no
        @reject
        Reject the order
    Close the call
```

`goto @call` goes up in the drawing, so it is an arrow loop. `goto @reject` goes down, so it is a shared join.
