# lai-gateway v0.1.31 Release Notes

v0.1.31 adds Gateway support for the Harness 0.4.5 MCP broker foundation. The release is intentionally visibility-only: it lets operators inspect MCP broker status, declared server/tool metadata, and policy decisions while continuing to deny MCP tool execution.

## Added
- `lai-gateway mcp status` for non-executing MCP broker status.
- `lai-gateway mcp tools` for declared MCP server/tool metadata.
- `lai-gateway mcp policy-check` for status, list-tools, and call-tool classification.
- `/v1/harness/mcp/status`, `/v1/harness/mcp/tools`, and `/v1/harness/mcp/policy-check` Gateway proxy routes.
- Local UI MCP Broker panel with status, tools, and call-tool denial checks.
- `mcp_broker` in `ops-status` and Telegram status notifications.
- `scripts/stack-check.sh`, the installed `lai-gateway-stack-check` wrapper, and `make milestone-gate` for local Gateway/Harness compatibility checks, including `--json` automation output that works from any current directory.
- Top-level `validation_command` and `validation_commands` in `release-check --json`, while retaining the existing validation check entry for compatibility.
- Fake-harness session-delete fixtures aligned with the real Harness `session.deleted` response shape.
- Installed private HTTP dogfood now covers a session-bound read-only run end to end: create session, create run, poll result, list by `control_run_id`, verify session persistence, and delete session.
- Gateway run-list handling normalizes legacy `run_id` records into `control_run_id`, and fake-harness run IDs now match the real `cr-<16 hex>` shape.
- Gateway run/session proxying now rejects malformed control IDs before contacting the Harness, and legacy `run_id` promotion is limited to real `cr-<16 hex>` IDs.
- Contract validation requires the full run/session route set used by the Gateway, including list and read endpoints.
- `scripts/publication-scan.sh` in `make check` to block private local path, known local IP, or blocked release-prose leakage from public release surfaces.
- `.gitignore` hardening for local private/runtime/build artifacts such as caches, logs, keys, VSIX, SQLite, GGUF, and `.secrets/`.
- Explicit setuptools build metadata and package discovery in `pyproject.toml`, with regression coverage for the console script, `lai_gateway*` package inclusion, test/docs/scripts exclusion, and static UI package data.

## Changed
- Gateway contract validation now requires the Harness 0.4.5 MCP foundation routes and capability flags.
- Shared JSON request parsing in the Gateway server now covers both read-only run creation and MCP policy-check bodies.
- Daily operations documentation now treats `mcp_broker` as part of the routine health snapshot.
- Fake Harness test fixtures now mirror the real MCP `decision` and `executed` response shape.

## Security
- MCP tool execution remains unavailable from every Gateway surface.
- `call-tool` checks are classification only and report `executed: false`.
- Private LAN mode requires gateway authentication for MCP proxy routes.
- No Harness control token, gateway token, pair token, Telegram token, or model API key is printed by MCP commands, API responses, UI assets, operations output, or Telegram status text.
- Public documentation examples avoid machine-specific local paths, IPs, and blocked release-prose phrases.
- Model file discovery defaults avoid machine-specific Windows user paths.

## Validation
- Full local validation passed with 193 tests.
- Installed `lai-gateway` session lifecycle dogfood passed from `/tmp` against a real temporary `lai serve`: create, list, get, and delete all succeeded with token output redacted and delete evidence under `session.deleted`.
- Installed private HTTP Gateway dogfood passed from `/tmp` against a real temporary `lai serve`: static UI stayed public, `/v1/harness/*` required gateway auth, and session create/list/get/delete succeeded without printing the Harness control token or Gateway access token.
- `make check` passed, including Python compile checks, shell syntax checks, publication scanning, optional static JS syntax checking, unittest discovery, TOML parsing, and `git diff --check`.
- `make milestone-gate HARNESS_REPO=../lai-local-agent TARGET_GATEWAY=0.1.31 TARGET_HARNESS=0.4.5` passed locally after running `make check` and the JSON stack compatibility gate; installed `lai-gateway-stack-check --json` also passed from `/tmp` with default sibling repo discovery and no stderr output.
- Local dogfood against `lai harness 0.4.5` confirmed MCP status, tool listing, policy-check denial, Gateway proxy routes, the UI MCP panel, and the local stack compatibility gate.
- Stack compatibility gate now requires the release-check JSON validation command fields used by automation.
- `lai-gateway release-check --json` resolves the Gateway checkout when the installed wrapper is launched from outside the repository.

## Notes
- `overall: no_config` is a valid MCP state when no MCP server configuration exists yet.
- Future MCP execution work should remain a separate milestone with an explicit threat model, allowlist, tests, and operator approval flow.
