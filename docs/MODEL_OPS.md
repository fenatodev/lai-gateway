# Local model operations

`lai-gateway` does not expose a direct llama.cpp or model API proxy through the mobile gateway. Local model execution belongs behind the harness/control plane boundary unless a separate threat model and tests exist.

## Inspect readiness

```bash
lai-gateway model-status
```

The command is read-only. It checks whether common local inference tools are available, whether a local model endpoint is configured, and whether the environment looks capable of a small local code model test. It does not start a server, download models, mutate files, or print secrets.

## Configure a local OpenAI-compatible endpoint

```bash
export LAI_GATEWAY_MODEL_BASE_URL='http://127.0.0.1:11434'
export LAI_GATEWAY_MODEL_NAME='<local-code-model>'
lai-gateway model-status --probe-openai
```

`--probe-openai` performs one bounded local `/v1/models` check against the configured endpoint. Leave it off when you only want offline readiness.

## Current project boundary

- No browser receives model API keys.
- No mobile route proxies arbitrary model prompts directly to llama.cpp.
- No model download is performed by `lai-gateway`.
- No benchmark result is claimed until a runtime and model are actually installed.

For Fenato's 8 GB GPU target, the next practical step is to install or expose one local runtime first, then test one small/quantized code model through the harness path instead of adding a raw model proxy.

## Safe endpoint probing

`lai-gateway model-status --probe-openai` only probes `GET /v1/models` after the configured base URL passes a local-safety gate. The probe is blocked before any network call when the URL uses HTTPS, embeds credentials, includes a query/fragment, omits an explicit port, or points at a public/non-private host.

The gateway UI exposes `/v1/gateway/model-status` as a read-only diagnostic endpoint. It does not probe the model backend by default, does not send prompts, does not download models, and requires gateway authentication when the gateway is running in private LAN mode.


## Runtime plan

Use `lai-gateway model-plan` before installing or starting a model backend. It is read-only: it does not download models, install packages, write config, or start servers.

Recommended first pass on this machine:

```bash
lai-gateway model-plan --backend auto --model-name '<local-code-model>'
```

After a runtime is actually listening, configure the local OpenAI-compatible endpoint and probe it:

```bash
export LAI_GATEWAY_MODEL_BASE_URL='http://127.0.0.1:11434'
export LAI_GATEWAY_MODEL_NAME='<local-code-model>'
lai-gateway model-status --probe-openai
```

The probe remains local/private only. Public hosts, embedded credentials, HTTPS, query strings, fragments, and URLs without an explicit port are blocked before any network call.
