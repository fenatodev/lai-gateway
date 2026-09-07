# lai-gateway

`lai-gateway` is a private companion gateway for `lai harness`.

It is intentionally a separate project. The harness owns local coding authority and guarded execution. The gateway owns private client adapters such as a future PWA or Telegram bot. That separation is not bureaucracy; it is how we avoid turning the core harness into a carnival ride with credentials.

## Current scope

The current gateway provides:

- a dependency-free Python client for the harness control plane;
- validation of the `lai harness v0.4.3` gateway contract;
- a local CLI for `config`, `contract`, `status`, `readiness`, `doctor`, `open-ui`, `sessions`, and `runs`;
- an HTTP gateway exposing harness status, readiness, contract, session, and read-only run routes, loopback by default with opt-in private LAN binding;
- read-only run creation for `diagnose`, `plan`, `release`, `review`, and `security`.

It does **not** expose write-capable run modes such as `implement`, `fix`, `refactor`, or `ci-fix`.

## Requirements

- Python 3.11+
- `lai harness` installed at `0.4.3+`
- `lai serve` running on loopback from the target harness repository directory
- a local LAI control token file

## Configuration

```bash
cp .env.example .env
```

Environment variables:

```bash
LAI_GATEWAY_HARNESS_URL=http://127.0.0.1:8765
LAI_GATEWAY_TOKEN_FILE=$HOME/.config/lai/control-api-key
LAI_GATEWAY_BIND=127.0.0.1
LAI_GATEWAY_PORT=8787
LAI_GATEWAY_PRIVATE_BIND=0
LAI_GATEWAY_ACCESS_TOKEN_FILE=$HOME/.config/lai-gateway/access-token
LAI_GATEWAY_PAIR_TOKEN_FILE=$HOME/.config/lai-gateway/pair-token.json
```

Create the separate gateway access token before using private LAN mode:

```bash
lai-gateway token create
lai-gateway token check
lai-gateway pair create --ttl-seconds 600 --show
lai-gateway pair check
```

The token file is created with `0600` permissions and the token is not printed by default. Prefer `lai-gateway pair create --show` for phone pairing; it creates a short-lived pairing token instead of exposing the permanent gateway token. For LAN access, set `LAI_GATEWAY_PRIVATE_BIND=1`, bind to a concrete private IP address, and create a separate gateway access token file. Do not use `0.0.0.0`; the gateway rejects wildcard and public binds. The browser UI may hold the gateway access token in page memory, but it still never receives the LAI harness control token. Repeated failed API auth attempts are rate-limited in memory. Pairing tokens are stored separately, expire automatically, and can be revoked with `lai-gateway pair revoke`.

Never commit a real token. Humanity has made many mistakes; do not add this one.

## CLI

Start the harness control plane from the repository you want LAI to operate on:

```bash
cd /path/to/lai-harness-checkout
lai serve --bind 127.0.0.1 --port 8765
```

Then query it through the gateway client:

```bash
python3 -m lai_gateway --version
python3 -m lai_gateway config
python3 -m lai_gateway contract
python3 -m lai_gateway status
python3 -m lai_gateway readiness
python3 -m lai_gateway doctor
python3 -m lai_gateway open-ui --print-only
python3 -m lai_gateway lan-info --port 8787
python3 -m lai_gateway mobile-access --port 8787
python3 -m lai_gateway mobile-bridge --target tailscale --port 8787
python3 -m lai_gateway mobile-bridge --target tailscale --port 8787 --apply
python3 -m lai_gateway telegram discover-chat --json
python3 -m lai_gateway telegram notify-mobile --port 8787
python3 -m lai_gateway telegram notify-status
python3 -m lai_gateway mobile-start --port 8787
python3 -m lai_gateway mobile-start --port 8787 --prepare
python3 -m lai_gateway mobile-start --candidate-ip 192.168.1.20 --port 8787
python3 -m lai_gateway mobile-serve --candidate-ip 192.168.1.20 --port 8787
python3 -m lai_gateway token create
python3 -m lai_gateway token check
python3 -m lai_gateway pair create --ttl-seconds 600 --show
python3 -m lai_gateway pair check
python3 -m lai_gateway pair revoke
python3 -m lai_gateway telegram token-check
python3 -m lai_gateway telegram token-set
python3 -m lai_gateway telegram token-repair-whitespace
python3 -m lai_gateway telegram bot-info
python3 -m lai_gateway telegram chat-check
python3 -m lai_gateway telegram chat-set --chat-id CHAT_ID_FROM_DISCOVER
python3 -m lai_gateway telegram preflight
python3 -m lai_gateway sessions list --limit 10
python3 -m lai_gateway sessions create
python3 -m lai_gateway sessions get <session_id>
python3 -m lai_gateway sessions delete <session_id>
python3 -m lai_gateway runs list --limit 10
python3 -m lai_gateway runs create --mode plan --task "Summarize the current state"
python3 -m lai_gateway runs create --mode review --session-id <session_id> --task "Review this safely"
python3 -m lai_gateway runs get <control_run_id>
```



## Local install and launcher

Install editable local wrappers without using `pip`:

```bash
scripts/install-local.sh
lai-gateway --version
lai-gateway doctor
```

Start the checked dev stack and open the UI:

```bash
lai-gateway dev --bind 127.0.0.1 --port 8787
# or
scripts/launch-local.sh --bind 127.0.0.1 --port 8787
```

The installer writes wrapper scripts to `$HOME/.local/bin` by default. Override that with `LAI_GATEWAY_INSTALL_BIN=/path/to/bin`. The wrappers point at this checkout and do not copy or print the LAI control token. The `dev` command runs `doctor` first and refuses to serve when the harness is not reachable or the local contract checks fail.

## Local UI

Start the harness and gateway, then open:

```text
http://127.0.0.1:8787/
```

The UI is intentionally local-first and phone-friendly. It can refresh readiness/status, show a local QR code for mobile access, guide mobile pairing with an in-memory checklist, create, inspect, and delete sessions, create read-only runs, poll selected runs, stop polling, keep a compact in-memory run history, fill read-only task presets, count task characters, and copy run output. Use `lai-gateway lan-info` to print private LAN URL candidates and safe startup commands without starting a server. Use `lai-gateway mobile-access` to show WSL/Windows/Tailscale phone URLs, QR data, and portproxy hints. Use `lai-gateway mobile-start --prepare` to create missing token files and refresh the short-lived pair token before opening the UI on a phone. Use `lai-gateway mobile-serve --candidate-ip <private-ip>` only when you intentionally want to prepare tokens and start the private LAN gateway in one foreground command. The phone UI keeps token state only in memory and exposes a Forget token control. In private mode, paste either the permanent gateway token or a short-lived pair token into the Gateway access card. Pair tokens are exchanged for temporary page-memory mobile sessions; the pair token is consumed and cannot directly access protected APIs. Forget token revokes the mobile session from server memory when possible and clears token state from the page. It does not receive the harness control token, does not use external CDN assets, and does not use browser storage. Tiny mercy in a world full of tracking pixels.


## Private LAN preview

Loopback remains the default. To inspect safe private LAN candidates without opening a port, run `lai-gateway lan-info --port 8787`. To inspect phone URLs and local QR data, run `lai-gateway mobile-access --port 8787`. To inspect whether the mobile gateway, token files, pair token, phone URL, and bridge look ready without starting anything, run `lai-gateway mobile-status --candidate-ip <private-ip> --port 8787`. To plan a persistent user service without starting or enabling it, run `lai-gateway service-plan --candidate-ip <private-ip> --port 8787`. When `systemctl --user` is unavailable, use `lai-gateway-mobile --candidate-ip <private-ip> --port 8787` after running `scripts/install-local.sh`. To inspect the whole local operation path in one read-only snapshot, run `lai-gateway ops-status --candidate-ip <private-ip> --port 8787`. To repair the common mobile path in one bounded step, run `lai-gateway mobile-repair --candidate-ip <private-ip> --port 8787 --prepare`; add `--bridge-listen-ip <windows-or-tailscale-ip> --apply-bridge` only from an elevated Windows context. In WSL2, use `lai-gateway mobile-bridge --target tailscale --port 8787` to print a Windows/Tailscale bridge plan, then `lai-gateway mobile-bridge --target tailscale --port 8787 --apply` from an elevated Windows/WSL shell to apply the portproxy/firewall rules. To get a guided mobile setup plan, run `lai-gateway mobile-start --port 8787`; add `--prepare` to create or refresh the separate gateway and pair-token files. If autodetection picks the wrong address, pass `--candidate-ip <private-ip>`. To intentionally prepare and serve in one step, run `lai-gateway mobile-serve --candidate-ip <private-ip> --port 8787`. To expose the gateway on a private LAN, use an explicit private address and a separate gateway token:

```bash
lai-gateway token create
lai-gateway token check
lai-gateway pair create --ttl-seconds 600 --show
lai-gateway pair check

LAI_GATEWAY_PRIVATE_BIND=1 \
LAI_GATEWAY_BIND=192.168.1.20 \
LAI_GATEWAY_ACCESS_TOKEN_FILE="$HOME/.config/lai-gateway/access-token" \
LAI_GATEWAY_PAIR_TOKEN_FILE="$HOME/.config/lai-gateway/pair-token.json" \
lai-gateway dev --no-open
```

When private mode is enabled, `/v1/harness/*` requires a permanent gateway access token or a temporary mobile session created from a one-shot pair token. Static UI files and `/healthz` remain secret-free. The UI keeps token state only in page memory, and Forget token revokes the mobile session before clearing the page when possible. The harness control token stays server-side. Token files must be `0600`, pairing tokens expire, and repeated failed API auth attempts return `429 gateway_auth_rate_limited`. Humanity gets one less obvious way to leak credentials.

## Telegram outbound notifications

Telegram support is outbound-only in this release. It does not expose a webhook and it does not let Telegram create harness runs. Configure a bot token file with `0600` permissions and a chat id, then explicitly enable sending:

```bash
chmod 600 "$HOME/.config/lai-gateway/telegram-bot-token"
LAI_GATEWAY_TELEGRAM_CHAT_ID=CHAT_ID_FROM_DISCOVER lai-gateway telegram preflight
LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1 LAI_GATEWAY_TELEGRAM_CHAT_ID=CHAT_ID_FROM_DISCOVER lai-gateway telegram send-message --text "lai-gateway ready"
```

The token value is never printed by `preflight` or `send-message`. Tiny outbreak of restraint.

## Gateway server MVP

```bash
python3 -m lai_gateway serve --bind 127.0.0.1 --port 8787
```

Routes:

```text
GET /healthz
GET /v1/harness/status
GET /v1/harness/readiness
GET /v1/harness/gateway-contract
GET /v1/harness/sessions?limit=N
POST /v1/harness/sessions
GET /v1/harness/sessions/{session_id}
DELETE /v1/harness/sessions/{session_id}
GET /v1/harness/runs?limit=N
POST /v1/harness/runs
GET /v1/harness/runs/{control_run_id}
```

Session routes can create, inspect, and delete persistent harness sessions. Run routes can create only read-only harness runs. `POST /v1/runs` remains blocked as a raw shortcut, and write modes remain rejected at the gateway boundary. That distinction matters unless your threat model was written on a napkin.

The gateway refuses wildcard and public bind addresses. Private-network/mobile exposure remains opt-in, private-token protected, and intentionally narrow.

## Development

```bash
make check
python3 -m lai_gateway release-check --target 0.1.15 --json
```

Release rules are documented in [docs/RELEASE.md](docs/RELEASE.md).

## License


Telegram setup should use `lai-gateway telegram token-set` instead of editing the token file by hand. `telegram token-check` reports redacted diagnostics, `telegram token-repair-whitespace` only rewrites the file when the compact token shape is valid, and `telegram bot-info` shows the public bot identity without reading messages or printing the token. `telegram chat-set` persists a discovered numeric chat id in `~/.config/lai-gateway/telegram-chat-id` with `0600` permissions; explicit `--chat-id` arguments and `LAI_GATEWAY_TELEGRAM_CHAT_ID` still override the file. Avoid shell placeholders such as `<chat_id>` or `<chat-id>`; `telegram discover-chat` prints concrete `chat-set` and export commands for discovered chats. Telegram API errors retain bounded, sanitized descriptions and include recovery hints for common setup failures such as `chat not found`.

MIT. See [LICENSE](LICENSE).


## Local model readiness

Use `lai-gateway model-status` to inspect local model runtime readiness without starting servers, downloading models, or exposing model secrets. See `docs/MODEL_OPS.md`.

For the full daily startup path after the published Harness and Gateway releases, see [docs/DAILY_OPS.md](docs/DAILY_OPS.md).

### Mobile Tailscale proxy

```bash
lai-gateway-mobile-proxy --target-host 172.29.193.62 --target-port 8787
```

For daily startup, use the wrapper that checks the published path end to end:

```bash
lai-gateway daily-config set \
  --candidate-ip 172.29.193.62 \
  --phone-url http://<your-device>.<your-tailnet>.ts.net:8787/

lai-gateway-daily --show-pair
```

Use this loopback proxy when Tailscale Serve needs to reach a WSL-bound mobile gateway through `http://127.0.0.1:18787`.


### Mobile pairing sessions

`lai-gateway-daily --show-pair` prints a short-lived pair token. The mobile UI
exchanges that token for a temporary page-memory session; no permanent gateway token
is stored on the phone.
