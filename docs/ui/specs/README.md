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
10. `10-onboarding-empty-states.md` — first-run guidance and empty states.
11. `11-keyboard-accessibility.md` — focus order, keyboard behavior, and accessible status.
12. `12-error-copy.md` — concise user-facing messages for failures and blocked actions.
13. `13-apply-confirmation.md` — explicit Apply confirmation and blocked promotion states.
14. `14-responsive-layout.md` — narrow viewport and mobile-safe layout constraints.
15. `15-incremental-roadmap.md` — staged implementation plan.
16. `16-transition-handoff.md` — how to pause and resume after system work.
17. `17-visual-qa-checklist.md` — manual QA checklist for the clean Workbench surface.
18. `18-restore-validation-matrix.md` — post-restore readiness matrix.
19. `19-final-pre-transition-scope.md` — frozen scope before hardware/OS transition.

## Transition docs

System transition docs live in `../../system-transition/` and should be read before resuming feature work after OS or disk changes.
## Non-goals

These specs do not authorize a terminal, arbitrary filesystem browser, editor, MCP execution, GitHub publication authority, or new Harness permissions. They only organize the existing secure Gateway/Harness surfaces.
