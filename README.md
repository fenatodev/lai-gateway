# lai-gateway

`lai-gateway` is a private companion gateway for `lai harness`.

It is intentionally a separate project. The harness owns local coding authority and guarded execution. The gateway owns private client adapters such as a future PWA or Telegram bot. That separation is not bureaucracy; it is how we avoid turning the core harness into a carnival ride with credentials.

## Current scope

The current gateway provides:

- a dependency-free Python client for the harness control plane;
- validation of the `lai harness v0.4.2` gateway contract;
- a local CLI for `config`, `contract`, `status`, `readiness`, `doctor`, `open-ui`, `sessions`, and `runs`;
- a loopback-only HTTP gateway exposing harness status, readiness, contract, session, and read-only run routes;
- read-only run creation for `diagnose`, `plan`, `release`, `review`, and `security`.

It does **not** expose write-capable run modes such as `implement`, `fix`, `refactor`, or `ci-fix`.

## Requirements

- Python 3.11+
- `lai harness` installed at `0.4.2+`
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
```

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
python3 -m lai_gateway sessions list --limit 10
python3 -m lai_gateway sessions create
python3 -m lai_gateway sessions get <session_id>
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

The UI is intentionally local-only. It can refresh readiness/status, create and inspect sessions, create read-only runs, poll selected runs, keep a compact in-memory run history, and copy run output. It does not receive the harness control token, does not use external CDN assets, and does not use browser storage. Tiny mercy in a world full of tracking pixels.

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
GET /v1/harness/runs?limit=N
POST /v1/harness/runs
GET /v1/harness/runs/{control_run_id}
```

Session routes can create and inspect persistent harness sessions. Run routes can create only read-only harness runs. `POST /v1/runs` remains blocked as a raw shortcut, and write modes remain rejected at the gateway boundary. That distinction matters unless your threat model was written on a napkin.

The gateway currently refuses public bind addresses. Private-network/mobile exposure belongs in a later spec with explicit authentication and threat modeling.

## Development

```bash
make check
python3 -m lai_gateway release-check --target 0.1.6 --json
```

Release rules are documented in [docs/RELEASE.md](docs/RELEASE.md).

## License

MIT. See [LICENSE](LICENSE).
