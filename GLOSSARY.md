# Drakon Editor

A standalone editor for DRAKON flowcharts, where one canonical data model is edited through both a text view and a canvas view.

## Language

**Diagram**:
A single DRAKON drawing, such as one business or workflow process.
_Avoid_: Schema, chart, flow

**Schema**:
The formal definition of the JSON format that a Model must conform to.
_Avoid_: Format spec, data definition

**Model**:
The JSON representation of a Diagram, and the single source of truth that every view reads and writes.
_Avoid_: Document, data, state

**Text view**:
A view that shows and edits the Model as human-writable text.
_Avoid_: Code view, DSL editor

**Canvas view**:
A view that shows and edits the Model as a drawn Diagram.
_Avoid_: Drawing view, preview

**Grammar**:
The DRAKON rules a Diagram must obey to be valid, such as the vertical main line and no crossing lines.
_Avoid_: Layout rules, constraints

**Host**:
Any page or application that embeds the editor and supplies or receives a Model.
_Avoid_: Container, parent app, integration

**Icon**:
One DRAKON element in a Diagram, such as an action, question or loop start.
_Avoid_: Item, node, shape

**Branch**:
One column of a silhouette Diagram, with a name, a first Icon, and ending in addresses or End.
_Avoid_: Lane, column, swimlane
