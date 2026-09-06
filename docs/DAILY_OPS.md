# Daily Operations

This runbook starts the published local LAI path without exposing secrets.

## Current proven path

- `lai harness` 0.4.3 runs the control plane on `127.0.0.1:8765`.
- `llama-server.exe` serves Qwen2.5-Coder on `172.29.192.1:8080` with `--api-key-file`.
- `lai-gateway` 0.1.24 serves the mobile UI on `172.29.193.62:8787`.
- Phone access uses the Windows/Tailscale URL `http://100.107.179.6:8787/` when the bridge is active.

## Start the model server

From the Harness checkout:

```bash
cd /home/fenato/dev/projects/lai-local-agent
lai-server-start
```

This is idempotent. If the authenticated model server is already running, it exits cleanly.

## Start the Harness control plane

```bash
cd /home/fenato/dev/projects/lai-local-agent
lai serve
```

Expected local URL:

```text
http://127.0.0.1:8765
```

## Start or repair the mobile gateway

From the gateway checkout:

```bash
cd /home/fenato/dev/projects/lai-gateway
export LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1
lai-gateway-mobile --candidate-ip 172.29.193.62 --port 8787 --telegram-notify
```

The launcher is idempotent. It checks the current state, repairs pair tokens when needed, and starts `mobile-serve` only when no listener is active.

## Check the Windows/Tailscale bridge

```bash
lai-gateway mobile-bridge --listen-ip 100.107.179.6 --connect-ip 172.29.193.62 --port 8787 --check
```

Expected result when the phone route is fully reachable:

```text
check: ready
```

If `listen_target` fails but `wsl_target` passes, the gateway is alive in WSL and the problem is on the Windows/Tailscale listener side. Apply or repair the bridge from an elevated Windows shell.

## Pair the phone

Generate a short-lived pair token only in your local terminal:

```bash
lai-gateway mobile-repair --candidate-ip 172.29.193.62 --port 8787 --prepare --show-pair
```

Paste the pair token into the phone UI only. Do not paste it into chat, GitHub, notes, logs, or screenshots.

## Notify the phone URL through Telegram

```bash
LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1 \
  lai-gateway telegram notify-mobile --candidate-ip 172.29.193.62 --port 8787
```

The Telegram message contains the mobile URL and bridge guidance only. It does not include pair, gateway, Harness, Telegram, or model API secrets.

## Check everything

```bash
LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1 \
  lai-gateway ops-status --candidate-ip 172.29.193.62 --port 8787
```

Expected operational state:

```text
harness_model: ready
mobile: ready
telegram: ready
gateway_model_probe: needs_model_config or ready
```

`gateway_model_probe` is a direct endpoint diagnostic. The normal product path uses the model behind the Harness, so `harness_model: ready` is the important daily signal.

## Mobile Tailscale proxy

```bash
lai-gateway-mobile-proxy --target-host 172.29.193.62 --target-port 8787
```

Point Tailscale Serve at `http://127.0.0.1:18787` and open the MagicDNS URL on the phone.
