# Embedding API shape

Type: grilling
Status: resolved
Blocked by:

## Question

How does a Host embed the editor: web component, `mount(el, options)`, or both; how does it pass a Model in and get it back out (methods, change events, read-only mode); and which views (Text, Canvas, both) can it show?

## Answer

Resolved by grilling, 2026-10-31. All ten recommendations accepted.

1. **Delivery form**: both. The core is `mount(el, options): Editor`. `<drakon-editor>` is a thin web-component wrapper: attributes for simple options, plus a `.editor` property exposing the full handle.
2. **Model in/out**: `options.model` sets the initial Model. `editor.getModel()` returns a copy, so Host mutation never reaches editor state. `editor.setModel(model)` replaces the Diagram and clears undo history.
3. **Change notification**: `onChange(model)` fires with the full Model once per committed edit (one undo step). Text view keystrokes only count once the text parses into a valid Model. The Host handles debouncing and saving.
4. **Invalid states**: an `onDiagnostics(list)` event and `editor.isValid()`. `onChange` stays silent while the text is invalid. The diagnostic format is deferred to the Grammar validation fog.
5. **Views**: `options.view: 'canvas' | 'text' | 'split'`, default `'split'`, changeable at runtime with `editor.setView()`. The editor fills the element it's mounted into, and the Host owns the layout around it.
6. **Read-only**: `readOnly: true` gives a Canvas viewer with no editing, toggled by `editor.setReadOnly()`. A static Model→SVG renderer belongs to the Export plugins fog.
7. **Insertions**: activating one fires `onInsertionActivate(diagramId)`. The editor never fetches, and the Host decides what happens.
8. **Bad input**: `mount` and `setModel` reject a Model that doesn't match the Schema with a typed error listing what's wrong, and nothing partial loads. drakonwidget import is a separate pure function, `importDrakonwidget(json): Model`.
9. **Lifecycle**: multiple instances per page, no global state. `editor.destroy()` removes all listeners and DOM.
10. **Packaging**: an ESM npm package with TypeScript types, plus one self-contained IIFE bundle for `<script>`-tag Hosts.
11. **Alignment guides**: `options.showAlignments` (default on in edit mode, off with `readOnly`), changeable at runtime with `editor.setShowAlignments()`. It controls only the guides and markers for alignment groups, never the Model (added 2026-11-02 by [Coordinates section semantics](04-coordinates-section-semantics.md)).

Deferred to the fog: patch-style change events (until a Host needs them), and Host-facing commands on the handle (undo/redo, zoom, focus), which belong to the editing model.
