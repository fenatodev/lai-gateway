# 18 — Restore validation matrix

This matrix separates system restoration checks from UI feature checks.

## System restoration

| Check | Command/source | Pass condition |
| --- | --- | --- |
| Gateway repo | Git status | clean `main` synced with origin |
| Harness repo | Git status | clean `main` synced with origin |
| Gateway version | CLI version | `0.1.34` or newer |
| Harness version | CLI version | `0.5.0` or newer |
| Model launcher | model status/smoke | ready with configured endpoint |
| UI assets | browser or curl | Workbench shell assets served |

## UI baseline

| Check | Evidence | Pass condition |
| --- | --- | --- |
| Shell | first load | chat/mode/status visible |
| Debug | first load | collapsed by default |
| Duplicate send guard | active run | second send blocked |
| Cancel guard | idle state | disabled when no run exists |
| Context reset | workspace/mode change | stale review/hash cleared |
## Feature readiness after restore

| Next feature | Required docs | Start condition |
| --- | --- | --- |
| Review Panel MVP | `04-review-panel.md`, `13-apply-confirmation.md` | baseline restored and tests pass |
| Guided onboarding | `10-onboarding-empty-states.md`, `12-error-copy.md` | Review Panel MVP merged |
| Sidebar polish | `06-project-sidebar.md`, `14-responsive-layout.md` | onboarding flow no longer blocks common use |
| Visual polish | `07-visual-system.md`, `11-keyboard-accessibility.md` | core flow stable |

## Stop conditions

Stop and fix restoration before feature work when:

- versions are older than the checkpoint;
- local model cannot pass smoke;
- tests fail for non-environmental reasons;
- UI assets do not reflect PRs `#51` and `#52`;
- repository state is dirty before new edits.
