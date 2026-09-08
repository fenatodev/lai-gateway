# Daily Operations

This runbook starts the published local LAI path without exposing secrets.

## Current proven path

- `lai harness` 0.4.5 runs the control plane on `127.0.0.1:8765` during local dogfood.
- `llama-server.exe` serves the validated Ministral baseline on `<wsl-default-gateway>:8080` with `--api-key-file`.
- `lai-gateway` 0.1.31 serves the mobile UI on `<wsl-gateway-ip>:8787` during local dogfood.
- Phone access uses the Tailscale Serve MagicDNS URL when the mobile proxy is active.

## Start the model server

From the Harness checkout:

```bash
cd ../lai-local-agent
lai-server-start
```

This is idempotent. If the authenticated model server is already running, it exits cleanly.

## Start the Harness control plane

```bash
cd ../lai-local-agent
lai serve
```

Expected local URL:

```text
http://127.0.0.1:8765
```

## Start or repair the mobile gateway

From the gateway checkout:

```bash
cd .
export LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1
lai-gateway-mobile --candidate-ip <wsl-gateway-ip> --port 8787 --telegram-notify
```

The launcher is idempotent. It checks the current state, repairs pair tokens when needed, and starts `mobile-serve` only when no listener is active.

## Check the Windows/Tailscale bridge

```bash
lai-gateway mobile-bridge --listen-ip <tailnet-ip> --connect-ip <wsl-gateway-ip> --port 8787 --check
```

Expected result when the phone route is fully reachable:

```text
check: ready
```

If `listen_target` fails but `wsl_target` passes, the gateway is alive in WSL and the problem is on the Windows/Tailscale listener side. Apply or repair the bridge from an elevated Windows shell.

## Pair the phone

Generate a short-lived pair token only in your local terminal:

```bash
lai-gateway mobile-repair --candidate-ip <wsl-gateway-ip> --port 8787 --prepare --show-pair
```

Paste the pair token into the phone UI only. Do not paste it into chat, GitHub, notes, logs, or screenshots.

## Notify the phone URL through Telegram

```bash
LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1 \
  lai-gateway telegram notify-mobile --candidate-ip <wsl-gateway-ip> --port 8787
```

The Telegram message contains the mobile URL and bridge guidance only. It does not include pair, gateway, Harness, Telegram, or model API secrets.

## Check everything

```bash
LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1 \
  lai-gateway ops-status --candidate-ip <wsl-gateway-ip> --port 8787
```

Expected operational state:

```text
harness_model: ready
mobile: ready
telegram: ready
gateway_model_probe: needs_model_config or ready
mcp_broker: no_config or ready
```

`mcp_broker` reports the Harness MCP broker foundation state. `no_config` is acceptable when no MCP server configuration exists yet; `call-tool` remains denied and non-executing in this milestone.

`gateway_model_probe` is a direct endpoint diagnostic. The normal product path uses the model behind the Harness, so `harness_model: ready` is the important daily signal.

## Mobile Tailscale proxy

```bash
lai-gateway-mobile-proxy --target-host <wsl-gateway-ip> --target-port 8787
```

Point Tailscale Serve at `http://127.0.0.1:18787` and open the MagicDNS URL on the phone.

## One-command daily startup

Once Tailscale Serve points at `http://127.0.0.1:18787`, the daily wrapper can validate and start the local path:

```bash
lai-gateway daily-config set \
  --candidate-ip <wsl-gateway-ip> \
  --phone-url http://<your-device>.<your-tailnet>.ts.net:8787/

lai-gateway-daily --show-pair
```

The wrapper keeps token values out of logs unless `--show-pair` is passed. It checks or starts `lai-server-start`, the harness control plane, `lai-gateway-mobile`, `lai-gateway-mobile-proxy`, and a final compact `health-report` snapshot.

For a dry plan without starting services:

```bash
lai-gateway-daily --candidate-ip <wsl-gateway-ip> --check-only
```


## Persist daily defaults

Use `daily-config` to save the local WSL/mobile IP and the phone URL without storing tokens:

```bash
lai-gateway daily-config set \
  --candidate-ip <wsl-gateway-ip> \
  --phone-url http://<your-device>.<your-tailnet>.ts.net:8787/
```

Then daily startup can be reduced to:

```bash
lai-gateway-daily --show-pair
```

The config file is stored with `0600` permissions and does not contain access tokens or pair tokens.
Use `LAI_GATEWAY_DAILY_CONFIG=/path/to/daily.json` when testing alternate profiles.


## Mobile read-only dogfood

Use `docs/MOBILE_READONLY_DOGFOOD.md` as the operator loop for health, pair refresh, session-bound read-only runs, sanitized event inspection, and rejected write attempts. The loop is deliberately limited to existing read-only Harness modes and does not enable MCP tool execution.

## Mobile session exchange

Phone pairing uses a short-lived pair token only to unlock a temporary mobile session.
The browser keeps the mobile session token in page memory only. It is not written to
localStorage, sessionStorage, or disk. The gateway stores only an in-memory hash of
active mobile sessions and consumes the pair token after a successful exchange. Pair
tokens are accepted only by the session exchange endpoint, not by protected Harness
or gateway API calls.

Daily flow:

```bash
lai-gateway-daily --show-pair
```

Open the printed phone URL, paste the temporary pair token, and tap **Pair this
phone**. The UI should report that a mobile session is active and show the session
countdown. If the page is closed or the session expires, run the daily command again
to print a fresh pair token. The **Forget token** button clears the browser token
and asks the gateway to revoke the active mobile session from server memory.

### Compact health report

For the final daily operator summary, prefer the compact report:

```bash
lai-gateway health-report --candidate-ip <wsl-private-ip> --port 8787
```

The Gateway UI shows this compact health report before the full operations detail so the daily answer is visible without reading raw JSON first. Use **Send health report to Telegram** only when you deliberately want a one-click status message; the backend still requires Telegram sending to be enabled to avoid accidental notifications.

It is read-only: it does not start servers, modify files, print token values, expose pair tokens, or enable MCP tool execution. Use `--telegram-notify` only when `LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1` is deliberately set for that shell.
