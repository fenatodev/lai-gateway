# PR: Prepare local model runtime and fixed evaluation flow

## Summary
- Detect Windows llama.cpp runtimes from WSL and prefer the proven Windows route before Docker.
- Add local GGUF model discovery with split-file grouping and recommendation logic for the Qwen2.5-Coder 7B local candidate.
- Add key-file setup/check commands, a `lai-gateway-model` launcher, fixed `model-smoke`, fixed `model-task`, and `model-eval`.
- Add prompt-free model run metrics and surface their summary through `ops-status`.
- Add UI/API read-only surfaces for model status, model plan, model files, fixed task/eval, and model run history.
- Align the gateway documentation with `lai harness v0.4.3` after the Harness runtime startup release.

## Safety boundaries
- No arbitrary prompt route is exposed through the mobile UI/API.
- No model download, package install, tunnel setup, public bind, or direct raw model proxy is introduced.
- Model endpoints are probed only after local/private HTTP URL validation.
- Model API keys are read from key files and are not printed, logged, or placed in process arguments.
- Private LAN mode requires gateway authentication for model operation endpoints.
- Metrics are opt-in and omit prompt text, full responses, Bearer values, and key paths.

## Validation
- `python3 -m compileall -q lai_gateway tests`
- `python3 -m py_compile lai_gateway/*.py tests/*.py`
- `bash -n scripts/*.sh`
- `python3 -m unittest discover -s tests -t . -v`
- `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`
- `git diff --check`
- `python3 -m lai_gateway release-check --target 0.1.23`

## Local dogfood
- `lai-gateway-model --eval --record` starts the Windows llama.cpp runtime, validates `/v1/models`, runs fixed smoke/task checks, and records prompt-free metrics.
- `lai-gateway model-status --probe-openai` reports `ready` against the local/private authenticated endpoint.
- A real read-only harness `plan` run succeeded through `lai-gateway -> lai harness v0.4.3 -> Qwen2.5-Coder`.
