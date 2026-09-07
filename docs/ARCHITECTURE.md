# Architecture

```text
private client later -> lai-gateway -> lai harness control plane -> local model/server
```

The gateway consumes the harness contract from:

```text
GET /v1/gateway-contract
```

The harness token stays in the gateway process. The token must not be sent to clients.

This project starts with a narrow read-only proxy because the next risky boundary is not HTML, Telegram, or styling. The next risky boundary is authority: who can ask the harness to run, write, promote, or cancel work.


## Repository scope

`lai serve` is cwd-sensitive by design. Start it from the target harness checkout, not from the `lai-gateway` project directory. The gateway is only a client adapter; it must not silently choose or mutate the harness repository.

## MCP broker boundary

Harness 0.4.5 owns MCP discovery and policy classification. The gateway proxies only the non-executing foundation routes:

```text
GET /v1/harness/mcp/status
GET /v1/harness/mcp/tools
POST /v1/harness/mcp/policy-check
```

The gateway treats MCP tool execution as denied authority. A `call-tool` policy check is classification only; it must return `executed: false` and must not start, call, or mutate external MCP servers. Protected MCP proxy routes follow the same private-mode gateway authentication boundary as the other `/v1/harness/*` routes.
