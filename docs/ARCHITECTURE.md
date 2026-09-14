# Architecture

The gateway is the user-facing coordination layer for LAI. It must not become a second harness or a second policy engine.

```text
client/interface -> lai-gateway -> core policy/tool boundary -> harness/adapters -> local model/server
```

## Current gateway scope

The gateway coordinates entry points, routing, model access and UI integration.

It must not silently choose or mutate a harness repository. `lai serve` is cwd-sensitive by design and should be started from the intended target checkout.

## Authority boundary

The next risky boundary is authority: who can ask the system to run, write, promote, apply, publish or call external tools.

Normative product contracts now live in:

```text
docs/product/lai_product_standard.md
docs/product/lai_architecture_decisions.md
docs/architecture/lai_architecture_contracts.md
docs/architecture/permission_model.md
docs/architecture/action_lifecycle.md
```

## Harness boundary

The harness owns dev-assisted execution, sandbox, review, promotion and approved apply.

Normal conversation must not start a harness run. `/plan` and `/work` are explicit dev entry points.

## MCP broker boundary

Harness 0.4.6+ owns MCP discovery and policy classification; Harness 0.4.8 is the current verified baseline.

The gateway proxies only non-executing foundation routes:

```text
GET /v1/harness/mcp/status
GET /v1/harness/mcp/tools
POST /v1/harness/mcp/policy-check
```

The gateway treats MCP tool execution as denied authority. A `call-tool` policy check is classification only; it must return `executed: false` and must not start, call, or mutate external MCP servers.

Protected MCP proxy routes follow the same private-mode gateway authentication boundary as other `/v1/harness/*` routes.
