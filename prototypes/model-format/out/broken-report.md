# Broken Diagrams: first error reported

## unknown Icon type

- own: **schema**: /icons/book value of tag "type" must be in oneOf
- JGF: **schema**: /graph/nodes/book/metadata value of tag "drakonType" must be in oneOf

## action without text

- own: **schema**: /icons/book must have required property 'text' 'text'
- JGF: **schema**: /graph/nodes/book must have required property 'label' 'label'

## question missing its 'no' exit

- own: **schema**: /icons/has-receipt must have required property 'no' 'no'
- JGF: **code**: 'has-receipt' (question) is missing exit 'no'

## question missing exit orientation (down)

- own: **schema**: /icons/has-receipt must have required property 'down' 'down'
- JGF: **schema**: /graph/nodes/has-receipt/metadata must have required property 'down' 'down'

## insertion without target Diagram id

- own: **schema**: /icons/finance must have required property 'diagram' 'diagram'
- JGF: **schema**: /graph/nodes/finance/metadata must have required property 'diagram' 'diagram'

## select with only one case

- own: **schema**: /icons/amount/cases must NOT have fewer than 2 items
- JGF: **code**: 'amount' select needs at least 2 cases

## dangling reference

- own: **code**: 'auto-approve' next -> unknown icon 'nowhere'
- JGF: **code**: 'auto-approve' next -> unknown icon 'nowhere'

## loop start not paired with a loop end

- own: **schema**: /icons/each-line must have required property 'end' 'end'
- JGF: **code**: 'each-line' (loopbegin) is missing exit 'end'

## unknown field on an Icon (typo `colour`)

- own: **schema**: /icons/book must NOT have additional properties
- JGF: **schema**: /graph/nodes/book/metadata must NOT have additional properties

## action with two `next` exits

- own: **cannot be written**: the format has no way to express this fault
- JGF: **code**: 'book' has more than one 'next' edge

## two cases with the same order

- own: **cannot be written**: the format has no way to express this fault
- JGF: **code**: 'amount' has case edges with duplicate order
