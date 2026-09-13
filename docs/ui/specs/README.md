# LAI Workbench UI spec pack

Status: design specs only. No implementation is included here.

This directory breaks the Workbench UI redesign into small, reviewable specs. The baseline spec is `../LAI-WORKBENCH-UI-SPEC.md`; the files here convert that direction into implementation-ready slices.

## Reading order

1. `01-information-architecture.md` — primary surface versus secondary panels.
2. `02-chat-composer.md` — central ChatGPT-like task entry and response pattern.
3. `03-run-state-machine.md` — frontend run transitions, polling, cancel, reconnect, and terminal states.
4. `04-review-panel.md` — files, validation, diff, and promotion readiness.
5. `05-debug-disclosure.md` — what Debug may expose and how it stays safe.
6. `06-project-sidebar.md` — project, session, and run navigation without a full IDE.
7. `07-visual-system.md` — density, spacing, visual hierarchy, and responsive rules.
8. `08-security-ux.md` — user-facing safety gates that mirror server-side authority boundaries.
9. `09-acceptance-fixtures.md` — test scenarios for future UI work.

## Non-goals

These specs do not authorize a terminal, arbitrary filesystem browser, editor, MCP execution, GitHub publication authority, or new Harness permissions. They only organize the existing secure Gateway/Harness surfaces.
