# lai-gateway v0.1.32 Release Notes

v0.1.32 aligns the Gateway with `lai harness` v0.4.6 and exposes the new read-only control-run event timeline through the CLI and private Gateway API. The release is intentionally narrow: it improves progress observability without enabling write-capable runs, raw shell, MCP tool execution, browser automation, or downloads.

## Added
- `lai-gateway runs events <control_run_id>` for bounded metadata-only run timelines.
- `GET /v1/harness/runs/{control_run_id}/events` as an authenticated Gateway proxy route.
- Gateway contract validation now requires the Harness run-event route in addition to the existing run/session/MCP foundation routes.

## Changed
- The default stack compatibility target now expects `lai harness` v0.4.6.
- Gateway package metadata is prepared for v0.1.32.

## Security
- Run-event payloads are defensively sanitized before leaving the Gateway. Exact fields named `stdout`, `stderr`, `task`, `task_text`, `turn`, `turns`, `transcript`, or `transcripts` are stripped recursively.
- The Gateway still allows only read-only run modes: `diagnose`, `plan`, `release`, `review`, and `security`.
- MCP support remains non-executing metadata and policy classification only.

## Validation
- Focused client, server, CLI, contract, and stack-check tests cover the event route and Harness v0.4.6 compatibility.
- `make check` and `make milestone-gate` should pass before tagging.

## Notes
- This release does not add a richer UI event panel yet. The API and CLI boundary come first so future PWA work can consume a tested route instead of inventing frontend behavior against hope, which is not a protocol.
