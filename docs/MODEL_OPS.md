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

## WSL with Windows llama.cpp

When `lai-gateway` runs inside WSL, `model-status` also checks Windows runtime tools exposed through the inherited Windows PATH, such as `llama-server.exe` and `llama-cli.exe`.

If Windows llama.cpp is detected, `model-plan --backend auto` prefers the `windows-llama-cpp` plan before Docker. This avoids ignoring an already-installed Windows runtime and prevents unnecessary container work.

The plan remains non-mutating: it does not download models, start `llama-server.exe`, change firewall rules, or expose a model proxy through the mobile gateway.

Use the generated `find_windows_host_from_wsl` command to identify the host address, start the Windows model server manually with a local GGUF model, then configure `LAI_GATEWAY_MODEL_BASE_URL` and verify with `model-status --probe-openai`.


## Local GGUF inventory

Use `model-files` before downloading anything:

```bash
lai-gateway model-files --max-results 10
```

It performs a bounded local scan only, groups split GGUF files, ignores accessory-only files such as `mmproj`, and recommends the best local candidate for the <=8 GiB code-model path.

On WSL with Windows llama.cpp available, the recommended command keeps the raw model behind `llama-server.exe` and still requires the normal `model-status --probe-openai` verification before any harness integration.


## Proven Windows llama.cpp route from WSL

For this machine, Windows llama.cpp was reachable from WSL when bound to the Windows vEthernet gateway, not Windows loopback and not the WSL DNS proxy:

```bash
ip route | awk '/default via/ {print $3; exit}'
```

Use the generated `model-files` recommendation. The validated shape is:

```bash
LLAMA_API_KEY='<set-local-model-api-key>' llama-server.exe --host <wsl-default-gateway> --port 18082 --model '<recommended-windows-gguf-path>' --ctx-size 2048 --threads 8 --n-gpu-layers 0 --cors-origins localhost --no-cors-credentials
export LAI_GATEWAY_MODEL_BASE_URL='http://<wsl-default-gateway>:18082'
export LAI_GATEWAY_MODEL_NAME='<recommended-model-name>'
export LAI_GATEWAY_MODEL_API_KEY='<same-local-model-api-key>'
lai-gateway model-status --probe-openai
```

A real smoke test loaded the local Qwen2.5-Coder 7B Q4_K_M split GGUF and returned `LAI_OK` through the OpenAI-compatible chat endpoint.


## Daily launcher

Use `lai-gateway-model` to start the recommended Windows llama.cpp runtime from WSL without copying long GGUF paths manually.

```bash
lai-gateway-model --create-key --smoke
```

For a dry run that prints the selected host, model, key-file path, and base URL without starting the runtime:

```bash
lai-gateway-model --plan-only
```

The launcher:

- uses `lai-gateway model-files` to pick the recommended local GGUF;
- creates or verifies a local model API key file without printing the key;
- starts `llama-server.exe` with `--api-key-file`, `--cors-origins localhost`, and `--no-cors-credentials`;
- binds to the WSL-reachable Windows gateway IP when available;
- waits for `/v1/models`, then runs `lai-gateway model-status --probe-openai`;
- with `--smoke`, runs `lai-gateway model-smoke` after readiness.

Never pass the model API key through a shell `curl -H` command. That exposes the secret in process arguments.


## Completion smoke test

After the local model endpoint is reachable, run a bounded fixed-prompt completion test:

```bash
lai-gateway model-smoke
```

`model-smoke` sends only a fixed health-check prompt asking the model to return `LAI_SMOKE_OK`. It does not accept arbitrary user prompts, does not download models, does not start servers, and does not print API keys.

Use it after:

```bash
export LAI_GATEWAY_MODEL_BASE_URL='http://172.29.192.1:18082'
export LAI_GATEWAY_MODEL_NAME='qwen2.5-coder-7b-instruct-q4_k_m'
export LAI_GATEWAY_MODEL_API_KEY_FILE='/mnt/c/Users/fenat/.config/lai-gateway/model-api-key'
lai-gateway model-status --probe-openai
lai-gateway model-smoke
```

Expected result:

```text
lai-gateway model-smoke: ready
matched: true
response_preview: LAI_SMOKE_OK
```

## Fixed model task

After `model-status --probe-openai` and `model-smoke` are ready, run the fixed code task:

```bash
lai-gateway model-task --task code-mini
```

The task asks for a tiny Python function and validates structural markers in the response. It is intentionally not a general prompt interface.

The local UI exposes the same fixed task through `/v1/gateway/model-task`; in private mode it requires the gateway bearer or pair token.

## One-command startup validation

Use the launcher to start the recommended Windows llama.cpp runtime and run both fixed validations:

```bash
lai-gateway-model --create-key --smoke --task
```

This starts the local runtime when needed, waits for `/v1/models`, runs `model-status --probe-openai`, runs `model-smoke`, and runs `model-task --task code-mini`. The key value stays in the key file and is not passed as a process argument.
