# Alignment text syntax mock-ups

Type: prototype
Status: open
Blocked by:

## Question

How are alignment groups (and the `compact` option) written in the Text view, so that a business analyst can read and author them? Icon text may contain `{`, `[` and `~` (code-heavy Icons), so the form must follow the same whole-word and quoting rules as the other suffixes (ticket 05 points 9, 29 and 31). The mock-ups should cover: two branches with one aligned step, an inert group with one member, a group that becomes active when a second member is added, a cycle that is reported, and `compact` on the `drakon` line. Extend the live Text view editor prototype (`prototypes/text-view-editor/`, branch `prototype/text-view-syntax`) rather than starting a new one.

## Context

- Decided in [Coordinates section semantics](04-coordinates-section-semantics.md): alignment groups `{id, label?, icons[]}`, inert groups of one, and a Diagram-level `compact` flag.
- Diagnostics follow [User-friendly diagnostics](09-user-friendly-diagnostics.md), including the cycle `error` that names both groups and the branches.
