# 09 — Acceptance fixtures

Status: spec only. No implementation.

## Goal

Define UI scenarios that future PRs can cover with static asset tests and fake Harness responses.

## Fixture groups

### Fresh load

- Contract not loaded.
- Workbench idle.
- Debug collapsed.
- No run id/hash fields visible in primary flow.

### Observe success

- Read-only mode returns succeeded.
- No changed files.
- Review stays closed.
- Summary says no files were changed.

### Work success with proposal

- Work run succeeds.
- Validation passes.
- Changed files present.
- Review opens or highlights.
- Apply is available only after review payload is bound.

### Work failure

- Run fails with safe error.
- Primary action becomes Inspect error or New task.
- Apply remains disabled.
- Debug may show sanitized events.

### Timeout

- Backend reports timeout.
- UI labels timeout distinctly from network failure.
- Retry is a new run, not hidden resume.

### Cancel

- User requests cancel.
- UI enters cancelling.
- Terminal cancelled appears only after backend confirmation.

### Disconnect/reconnect

- Polling fails while run may still exist.
- UI offers reconnect and preserves run reference internally.
- No duplicate task is sent automatically.

### Stale review

- User switches workspace or run.
- Patch sha is cleared.
- Apply becomes disabled.

### Private/mobile access

- Read-only endpoints work with auth.
- Work/review/promotion remain unavailable outside allowed loopback mode.
- Output remains safe for display.

## Acceptance

A future UI PR should add or update only fixtures relevant to its slice. Avoid large all-at-once browser behavior rewrites.
