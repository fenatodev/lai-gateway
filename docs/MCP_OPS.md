# MCP Operations

This runbook covers the Gateway 0.1.32 integration with the Harness 0.4.6 MCP broker foundation.

## Boundary

The MCP foundation is intentionally non-executing. The gateway may ask the harness for broker status, declared server/tool metadata, and a policy classification for a requested MCP operation. It must not execute an MCP tool, start a remote MCP server, print credentials, or expose the Harness control token to clients.

## Local checks

Start the harness control plane from the target harness checkout:

```bash
cd ../lai-local-agent
lai serve --bind 127.0.0.1 --port 8765
```

From the gateway checkout:

```bash
cd .
lai-gateway mcp status
lai-gateway mcp tools
lai-gateway mcp policy-check --operation call-tool --server desktop-commander --tool start_process
```

Expected `call-tool` safety result:

```text
decision: DENY
executed: false
```

`overall: no_config` is a valid foundation state when the harness has no MCP configuration files. It means discovery found no configured servers; it is not permission to execute anything.

## Gateway HTTP proxy

The local gateway exposes these protected proxy routes:

```text
GET /v1/harness/mcp/status
GET /v1/harness/mcp/tools
POST /v1/harness/mcp/policy-check
```

In loopback mode, these routes rely on the server-side Harness control token. In private LAN mode, they also require a gateway access token or active mobile session, matching the rest of `/v1/harness/*`. Pair tokens cannot call these routes directly; they can only be exchanged for a temporary mobile session.

## Defensive redaction

The gateway treats MCP payloads as untrusted metadata. Before MCP status, tools, or policy-check responses reach CLI, API, UI, ops-status, or Telegram output, secret-shaped fields such as authorization headers, API keys, passwords, and token values are replaced with `[redacted-mcp-secret]`. Safe boolean security flags such as `executes_tools`, `prints_credentials`, and `reads_env_values` are preserved so operators can still diagnose the boundary.

## Ops status

Use the read-only operations snapshot to include MCP in the daily health view:

```bash
lai-gateway ops-status --candidate-ip <wsl-gateway-ip> --port 8787
```

Relevant line:

```text
mcp_broker: no_config
```

For this milestone, safe states are `ready` or `no_config`. A blocked MCP state should be treated as a configuration problem before any future MCP execution work is considered.

## Stack compatibility gate

Use the local stack gate before committing or publishing coordinated Gateway/Harness work:

```bash
bash scripts/stack-check.sh --harness-repo ../lai-local-agent --target-gateway 0.1.31 --target-harness 0.4.6
bash scripts/stack-check.sh --harness-repo ../lai-local-agent --target-gateway 0.1.31 --target-harness 0.4.6 --json
lai-gateway-stack-check --harness-repo ../lai-local-agent --target-gateway 0.1.31 --target-harness 0.4.6 --json
make milestone-gate HARNESS_REPO=../lai-local-agent TARGET_GATEWAY=0.1.32 TARGET_HARNESS=0.4.6
```

The gate validates the Gateway version, Harness version, Harness gateway contract, MCP status safety flags, `call-tool` denial, MCP help output, and Gateway release-check version/safety signals. The stack gate also asserts the release-check JSON validation command fields used by automation. A dirty checkout is reported but allowed because this gate is intended for pre-commit validation. The installed wrapper resolves the Gateway checkout before release checks, so it can be launched from outside the repository.
