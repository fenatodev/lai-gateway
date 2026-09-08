# Mobile read-only dogfood

This document defines the current mobile-safe dogfood loop for `lai-gateway`.
It is intentionally limited to existing read-only Harness capabilities.

## Scenarios

### Scenario 1: health and access readiness

Goal: confirm that the phone-facing gateway is reachable and safe before creating runs.

Operator path:
1. Run `lai-gateway health-report`.
2. If mobile reports `needs_pair`, run `lai-gateway mobile-start --prepare`.
3. Use the UI health card or `health-report --telegram-notify` only when sending is explicitly enabled.

Expected result: health is `ready`, `next_steps` is empty, and no token, pair token, chat id, local path, or MCP credential value is printed.

### Scenario 2: session-bound diagnose run

Goal: prove that a phone user can create a session, start a read-only run, inspect progress events, and later reuse or forget the session.

Operator path:
1. Create a session with `lai-gateway sessions create` or the UI session action.
2. Create a read-only `diagnose` run with that session.
3. Poll `runs get` until terminal.
4. Inspect `runs events` for metadata-only progress.
5. Read the session again or delete it when done.

Expected result: only read-only modes are accepted; run/event/session payloads omit repository paths, stdout, stderr, task text, transcripts, token values, pair tokens, chat ids, and private runtime files.

### Scenario 3: rejected write attempt

Goal: prove the mobile path cannot escalate into Harness write authority.

Operator path:
1. Attempt to create a run with a write-capable mode such as `implement`.
2. Attempt malformed run/session IDs.

Expected result: the Gateway rejects the request before proxying it to the Harness.

## Repeatable command

Run the bounded loop from the Gateway checkout:

```bash
bash scripts/mobile-readonly-dogfood.sh
```

Optional environment overrides:

- `LAI_GATEWAY_DOGFOOD_MODE`, default `diagnose`;
- `LAI_GATEWAY_DOGFOOD_TASK`, default read-only status check;
- `LAI_GATEWAY_DOGFOOD_POLL_LIMIT`, default `12`;
- `LAI_GATEWAY_DOGFOOD_POLL_SECONDS`, default `2`.

The script uses existing Gateway CLI routes. It does not create pair tokens, print tokens, enable MCP execution, or expose write-capable Harness modes.

## Evidence

Initial baseline found that session and run payloads were machine-readable but included Harness repository path metadata. The client sanitizer now removes those fields from CLI and HTTP responses for session/run/event paths.

A local-private dogfood loop then completed a session-bound `diagnose` run with sanitized session, run, and event payloads. The same loop is now covered by `scripts/mobile-readonly-dogfood.sh` and `tests.test_scripts.ScriptTest.test_mobile_readonly_dogfood_script_uses_sanitized_read_only_loop`.
