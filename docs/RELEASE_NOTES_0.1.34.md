# lai-gateway v0.1.34 Release Notes

v0.1.34 aligns the Gateway with `lai harness` v0.4.7 after the Harness control-run event timeline was enriched. The release is intentionally narrow: it updates compatibility defaults, docs, and fixtures without adding new Gateway authority.

## What changed

- Gateway package version is now 0.1.34.
- Default stack compatibility target now expects `lai harness` v0.4.7.
- Current Gateway documentation now names the Harness v0.4.7 baseline for run-event timelines.
- Test fixtures and stack-check coverage now use Harness v0.4.7 responses.

## Safety boundary

- No new write-capable Gateway routes.
- No shell, browser automation, downloads, MCP tool execution, credential persistence, push, PR, tag, or release authority is added.
- Existing run-event payload sanitization remains in place.

## Validation

Run:

```bash
make check
make milestone-gate HARNESS_REPO=../lai-local-agent TARGET_GATEWAY=0.1.34 MIN_HARNESS=0.4.6
lai-gateway-stack-check --json
```
