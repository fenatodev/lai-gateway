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
