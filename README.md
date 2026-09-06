# lai-gateway

`lai-gateway` is a private companion gateway for `lai harness`.

It is intentionally a separate project. The harness owns local coding authority and guarded execution. The gateway owns private client adapters such as a future PWA or Telegram bot. That separation is not bureaucracy; it is how we avoid turning the core harness into a carnival ride with credentials.

## Current scope

This first cut only provides:

- a dependency-free Python client for the harness control plane;
- validation of the `lai harness v0.4.2` gateway contract;
- a local CLI for `config`, `contract`, `status`, and `readiness`;
- a loopback-only HTTP gateway MVP exposing read-only harness status, readiness, and contract routes.

It does **not** expose run creation yet.

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
```

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
```

The gateway currently refuses public bind addresses. Private-network/mobile exposure belongs in a later spec with explicit authentication and threat modeling.

## Development

```bash
make check
```

## License

MIT. See [LICENSE](LICENSE).
