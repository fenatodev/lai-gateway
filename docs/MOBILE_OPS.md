# Mobile operations

`lai-gateway` keeps the mobile path explicit because phone access crosses several trust boundaries: WSL, Windows networking, Tailscale/LAN routing, browser pairing, and Telegram notifications. The commands below are designed to make that path repeatable without exposing tokens.


## Full operations snapshot

```bash
lai-gateway ops-status --candidate-ip <wsl-ip> --port 8787
```

This combines `doctor`, `mobile-status`, and Telegram preflight into one read-only report. It is the fastest way to see whether the local harness, mobile gateway, pair token, phone URL, and Telegram configuration are usable.

## Fast status

```bash
lai-gateway mobile-status --candidate-ip <wsl-ip> --port 8787
```

This is read-only. It reports the listener, gateway access token, pair token, phone URL, WSL bridge hints, and next steps.

## Repair tokens without starting a server

```bash
lai-gateway mobile-repair --candidate-ip <wsl-ip> --port 8787 --prepare
```

This creates or refreshes the gateway access/pair-token files as needed. It does not start a server and does not print token values by default. Use `--show-pair` only when you are actively pasting the short-lived token into the phone UI.

## Plan or apply the Windows/Tailscale bridge

```bash
lai-gateway mobile-repair \
  --candidate-ip <wsl-ip> \
  --port 8787 \
  --bridge-listen-ip <windows-or-tailscale-ip>
```

Add `--apply-bridge` only from an elevated Windows/WSL shell. Bridge setup forwards a selected Windows/Tailscale IPv4 address to the WSL gateway. It does not involve gateway, harness, pair, or Telegram tokens.

## Start serving

```bash
lai-gateway mobile-serve --candidate-ip <wsl-ip> --port 8787 --telegram-notify
```

`mobile-serve` starts the foreground gateway. If the port is already occupied, it now fails before creating fresh pair tokens or sending Telegram notifications.

## Security boundaries

- Status is read-only.
- Token file mutation requires `--prepare`.
- Windows network mutation requires `--apply-bridge`.
- Pair-token printing requires `--show-pair`.
- Telegram sending still requires `LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1`.
- The browser never receives the LAI harness control token.

## Persistent user service

```bash
lai-gateway service-plan --candidate-ip <wsl-ip> --port 8787 --telegram-notify
```

This prints a token-free `systemd --user` plan for running `mobile-serve` as a persistent foreground service. It does not write files, enable the unit, or start anything. To write only the unit file:

```bash
lai-gateway service-install --candidate-ip <wsl-ip> --port 8787 --telegram-notify
```

Then enable it manually when the plan looks right:

```bash
systemctl --user daemon-reload
systemctl --user enable --now lai-gateway-mobile.service
systemctl --user status lai-gateway-mobile.service
```

Remove only the unit file with:

```bash
lai-gateway service-remove
```

The service unit stores token file paths, not token values. Starting and enabling the service remain explicit `systemctl --user` steps.


## Idempotent launcher fallback

When `systemctl --user` is not available, use the wrapper installed by `scripts/install-local.sh`:

```bash
lai-gateway-mobile --candidate-ip <wsl-ip> --port 8787 --telegram-notify
```

The launcher is intentionally idempotent. If the mobile gateway is already ready, it prints `ops-status` and exits. If the listener is active but the pair token is stale, it refreshes mobile tokens and exits. If there is no listener, it prepares tokens and starts `mobile-serve` in the foreground.
