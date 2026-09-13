# 08 — Security UX

Status: spec only. No implementation.

## Goal

Make safety visible without training users to manage raw security mechanisms manually.

## Boundaries to preserve

- Harness owns local execution authority.
- Gateway presents UI and safe API orchestration.
- Work/review/promotion are loopback-only.
- Private/mobile mode remains read-only where current policy requires it.
- Server-side checks remain authoritative.

## User-facing safety copy

Prefer precise copy:

- “Work runs in sandbox.”
- “Review is required before applying.”
- “Apply is blocked because validation failed.”
- “This view is read-only from mobile/private access.”

Avoid misleading copy:

- “Rollback completed” when only browser state was discarded.
- “Applied” before backend confirmation.
- “Safe” when evidence is missing.

## Confirmation requirements

Promotion confirmation must include:

- project/workspace display name;
- changed file count;
- validation state;
- short hash prefix;
- warning that applying changes the target through Harness gates.

Never ask the user to paste a hash in normal mode. Hash is an internal binding from reviewed payload to promotion request.

## Unsafe states

Block Apply when:

- patch hash missing or malformed;
- review belongs to another run/workspace;
- validation failed, missing, or stale;
- diff is materially truncated;
- backend reports drift;
- current access mode is not loopback;
- required capability is absent.

## Acceptance

- Button hiding is never the only enforcement.
- UI tests assert private/mobile work surfaces remain denied.
- Debug/copied data remains credential-free and path-safe.
