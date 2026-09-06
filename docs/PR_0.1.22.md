# PR: Complete mobile ops, service fallback, and model readiness diagnostics

## Summary
- Add a batched `ops-status` snapshot covering doctor, mobile, Telegram, and local model readiness.
- Add `mobile-repair` for safe pair-token refresh and bridge repair planning without starting servers by default.
- Add systemd-user service planning/install/remove plus an idempotent `lai-gateway-mobile` fallback launcher for WSL environments where `systemd --user` is unavailable.
- Add local model readiness support with `model-status`, safe OpenAI-compatible probing, and `model-plan` preparation guidance.
- Add UI/API panels for Operations and Model visibility.

## Safety boundaries
- Diagnostics are read-only by default.
- No gateway, pair, Telegram, harness, or model API secrets are printed.
- Model probing blocks public, credentialed, HTTPS, query-bearing, fragment-bearing, or portless URLs before network access.
- Private LAN mode requires gateway auth for ops/model endpoints.
- No direct llama.cpp/model proxy is exposed to the mobile UI.
- No automatic model downloads, package installs, tunnel setup, or service start/enable behavior.

## Validation
- `python3 -m compileall -q lai_gateway tests`
- `python3 -m py_compile lai_gateway/*.py tests/*.py`
- `bash -n scripts/*.sh`
- `python3 -m unittest discover -s tests -t . -v`
- `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`
- `git diff --check`
- `python3 -m lai_gateway release-check --target 0.1.22`

## Local dogfood
- `lai-gateway model-plan --backend auto --model-name qwen-code-local`
- `lai-gateway model-status --probe-openai` blocks unsafe public endpoints before network access.
- `/v1/gateway/model-plan` and `/v1/gateway/model-status` return secret-free read-only JSON.
