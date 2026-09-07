# PR: Add non-executing MCP broker visibility

## Summary
- Add Gateway client, CLI, HTTP proxy, UI, and operations surfaces for the Harness 0.4.5 MCP broker foundation.
- Validate the Harness MCP contract routes and capability flags before treating the gateway contract as compatible.
- Expose MCP status, declared tool metadata, and policy classification without enabling MCP tool execution.
- Add `mcp_broker` to `ops-status` and Telegram status notifications so the daily path reports MCP readiness.
- Document the MCP boundary in README, architecture, daily operations, and the dedicated MCP runbook.
- Add a local stack compatibility gate for Gateway 0.1.31 plus Harness 0.4.5.

## Safety boundaries
- No MCP tool execution is exposed through CLI, HTTP, UI, Telegram, or operations status.
- `call-tool` remains a policy classification only and must return `executed: false`.
- Private LAN mode protects `/v1/harness/mcp/*` with the same gateway auth boundary as other Harness proxy routes.
- The Harness control bearer token remains server-side and is never sent to clients.
- MCP config status may be `no_config`; that is a safe discovery state, not execution permission.
- Secret-shaped upstream MCP fields are redacted before CLI, HTTP, UI, ops, or Telegram exposure.
- Public release surfaces are scanned for private local path, known local IP, or blocked release-prose leakage.
- `.gitignore` blocks local private/runtime/build artifacts from routine commits.
- `pyproject.toml` declares the setuptools build backend, console script, package discovery limited to `lai_gateway*`, test/docs/scripts package exclusion, and static UI package data explicitly.
- `release-check --json` exposes `validation_command` and `validation_commands` at top level for automation and keeps the validation check entry for compatibility.
- Persistent-session delete fixtures match the real Harness `session.deleted` response shape.
- Gateway contract validation requires the full run/session route set used by the Gateway, including list and read endpoints.
- Windows/WSL model discovery roots are generic and do not bake in a local user profile.

## Validation
- `python3 -m py_compile lai_gateway/*.py tests/*.py`
- `python3 -m unittest tests.test_harness_client tests.test_contract tests.test_cli tests.test_gateway_server tests.test_ops -v`
- `python3 -m unittest tests.test_harness_client tests.test_gateway_server tests.test_cli -v` for MCP redaction coverage and CLI ergonomics.
- `python3 -m unittest tests.test_telegram tests.test_ui tests.test_ops -v`
- `make check`, including publication scan and optional `node --check lai_gateway/static/app.js` when Node is available locally.
- `bash scripts/stack-check.sh --harness-repo ../lai-local-agent --target-gateway 0.1.31 --target-harness 0.4.5`.
- `bash scripts/stack-check.sh --harness-repo ../lai-local-agent --target-gateway 0.1.31 --target-harness 0.4.5 --json`, plus installed `lai-gateway-stack-check --json` from outside the repository with default sibling repo discovery.
- Stack compatibility gate asserts the release-check JSON validation command fields used by automation.
- `lai-gateway release-check --json` is covered when launched from outside the repository through the installed wrapper path.
- Installed private HTTP dogfood covers session-bound read-only run creation, polling, list lookup, session persistence, and session deletion against a real temporary `lai serve`.
- Gateway run-list handling accepts both `control_run_id` and legacy `run_id` payloads so the UI can select listed runs from real Harness responses.
- Gateway validates `cr-<16 hex>` and `cs-<16 hex>` control identifiers before proxying run/session get/delete requests.
- Installed `lai-gateway` session lifecycle dogfood from `/tmp` against a real temporary `lai serve`, covering create/list/get/delete without printing the control token.
- Installed private HTTP Gateway dogfood from `/tmp` confirmed static UI access, protected `/v1/harness/*` auth, and session create/list/get/delete against a real temporary Harness.
- `make milestone-gate HARNESS_REPO=../lai-local-agent TARGET_GATEWAY=0.1.31 TARGET_HARNESS=0.4.5`.
- Real local dogfood against `lai harness 0.4.5` for CLI MCP commands and `/v1/harness/mcp/*` proxy routes.

## Local dogfood
- `lai-gateway mcp status` returns Harness 0.4.5 MCP status with `overall: no_config` when no MCP config is present.
- `lai-gateway mcp tools` returns `execution_enabled: false` without starting MCP servers.
- `lai-gateway mcp policy-check --operation call-tool --server desktop-commander --tool start_process` returns `decision: DENY` and `executed: false`.
- The local UI serves an MCP Broker panel and proxies MCP status/tools/policy-check through the gateway boundary.
- Installed `lai-gateway sessions create/list/get/delete` works from `/tmp` against a temporary loopback `lai serve`; session delete evidence is returned under `session.deleted`.
- Installed private HTTP Gateway session lifecycle works from `/tmp` with a separate gateway access token; unauthenticated Harness proxy routes return 401 while static UI remains secret-free.
