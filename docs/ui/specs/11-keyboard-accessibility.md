# 11 — Keyboard and accessibility

Status: spec only. No implementation.

## Goal

Make the Workbench usable from keyboard, screen readers, and narrow/mobile layouts without losing safety context.

## Keyboard rules

- Tab order follows visual order: project, mode, composer, primary action, secondary action, review, Debug.
- Escape closes non-critical drawers but does not cancel a run.
- Enter behavior in textarea must preserve multiline input unless an explicit shortcut is documented.
- Promotion confirmation must be reachable and understandable without mouse input.

## Accessible states

Use text plus ARIA live regions for:

- run state changes;
- validation result;
- review availability;
- Apply blocked reason;
- network/polling errors.

## Focus management

- After run start, focus stays predictable and does not jump into Debug.
- When review becomes available, announce it and offer a focusable Review button.
- After failed validation, focus moves to the safe error summary only if it will not interrupt typing.

## Acceptance

- Full Observe and Work-to-review flow can be operated by keyboard.
- Color is never the only status signal.
- Debug collapse/expand is accessible.
