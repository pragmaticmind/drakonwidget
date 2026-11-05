# DRAKON example corpus

147 structurally distinct DRAKON diagrams, used to check whether real-world diagrams can be represented in the text syntax (see `prototypes/text-syntax`).

Each file is one diagram in the upstream DrakonWidget/DrakonTech JSON format (`items`, `one`/`two` links, `keywords`, `params`). `manifest.json` lists every file with its origin, node count and feature tags.

## Sources

- `drakonhub/` (16): `drakon_examples` in stepan-mitkin/drakonhub_desktop. Real-life flowcharts with headers, comments, callouts, durations and styles.
- `drakonwidget/` (7): `js/examples.js` in stepan-mitkin/drakonwidget. Includes the only parallel (`parbegin`/`parend`), `insertion` and `group-duration` samples.
- `drakontech/` (124): `examples` in stepan-mitkin/drakon.tech.desktop. Loops, select/case, silhouettes, state machines and classes. The upstream repo repeats each diagram per target language, so duplicates were removed by comparing structure while ignoring text.

All three upstream repos are released under The Unlicense.

## Feature coverage (unique diagrams)

question 83, silhouette 32, loopbegin/loopend 30, flipped Yes/No 34, arrow-loop 22, select 22, case 22, header 16, action side-link 11, style 9, sinput 6, comment 4, callout 4, duration 2, insertion 2, async 2, parbegin/parend 1, group-duration 1.

## Notes for validation

- Merged flows (several icons pointing at one icon) and arrow-loop back-edges are the likely hard cases for a tree-like text syntax.
- Layout coordinates (callouts) and per-icon `style` are probably not round-trippable and may need to be dropped or kept as optional attributes.
