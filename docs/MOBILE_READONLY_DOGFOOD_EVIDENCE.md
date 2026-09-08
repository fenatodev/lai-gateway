# Mobile read-only dogfood evidence

## Baseline

A local-private Gateway-to-Harness loop was exercised through the same session and run APIs used by the phone UI.

The first baseline showed:

- `sessions create`, `runs create`, `runs get`, `runs events`, and `sessions get` returned machine-readable JSON without requiring a `--json` flag.
- `runs events` already removed stdout, stderr, raw task text, and transcript fields.
- Session and run payloads still included top-level Harness repository metadata, which can expose a local checkout path.

## Fix

Gateway HarnessClient now sanitizes the session/run/event mobile surface by:

- removing `repository`, `workspace_path`, `root_path`, `cwd`, `metrics_file`, and `audit_file` fields;
- removing stdout, stderr, task text, and transcript fields from session/run/event payloads;
- redacting absolute Linux and Windows user-profile paths if any survive in string values;
- preserving safe relative project paths where useful for operator context.

## Dogfood after fix

A session-bound read-only `diagnose` run completed through Gateway CLI using the live Harness control plane.

Observed sanitized payload results:

- session create: no repository field, no local path, no raw output fields, no token-shaped content;
- run create: no repository field, no local path, no forbidden raw keys, no token-shaped content;
- run get: no repository field, no local path, no forbidden raw keys, no token-shaped content;
- run events: seven metadata-only events, no local path, no raw output fields, no token-shaped content;
- session get: no repository field, no local path, no raw output fields, no token-shaped content.

## Repeatable dogfood script

The loop is now captured in `scripts/mobile-readonly-dogfood.sh`.

The script verifies:

- write-capable run modes are rejected;
- a Harness session can be created;
- a read-only session-bound run can be created and polled to a terminal state;
- run events are available as metadata-only progress;
- session get/delete works after the run;
- every JSON response is scanned for forbidden raw fields, repository metadata, local paths, chat ids, pair tokens, Bearer strings, and token-shaped Telegram values.

Validation results:

- live Gateway-to-Harness dogfood: `mobile-readonly-dogfood: ready`;
- focused script/client/CLI/server tests: `55 tests OK`;
- full Gateway `make check`: `209 tests OK`.

## Remaining work

M2 has enough evidence for a first integration cut without adding UI. Future UI work should be triggered only by repeated phone friction that this script cannot cover. Do not add write modes, MCP execution, browser automation, or automatic recurring notifications.
