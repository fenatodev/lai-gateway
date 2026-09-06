# lai-gateway v0.1.23 Release Notes

v0.1.23 turns the local model path from diagnostics into a repeatable operating flow. It discovers the local GGUF model, starts the Windows llama.cpp runtime from WSL, validates the authenticated endpoint, runs fixed model checks, and records prompt-free metrics.

## Added
- Windows llama.cpp runtime detection from WSL.
- `lai-gateway model-files` for local GGUF discovery, split-file grouping, and code-model recommendation.
- `lai-gateway model-key-create` and `model-key-check` for secret-free model API key-file setup.
- `lai-gateway-model`, an idempotent local model launcher for Windows llama.cpp from WSL.
- `lai-gateway model-smoke`, `model-task`, and `model-eval` for fixed, bounded local model validation.
- `model-smoke --record`, `model-task --record`, `model-runs`, launcher `--record`, and prompt-free model run metrics.
- Model files, task, eval, and run-history endpoints plus matching UI actions.
- Model run summary in `ops-status`.

## Changed
- Documented baseline is now `lai harness v0.4.3+`.
- Windows llama.cpp planning uses the WSL default gateway and `--ctx-size 4096`, matching the real harness run requirement.
- `model-status --probe-openai` can read `LAI_GATEWAY_MODEL_API_KEY_FILE`.
- `lai-gateway-model --plan-only` no longer requires an existing key file.
- Windows key-file paths are derived from the discovered model path instead of the WSL username.

## Security
- No arbitrary prompt route is exposed through the mobile UI/API.
- Model probing rejects public, credentialed, HTTPS, query-bearing, fragment-bearing, or portless endpoints before network access.
- The recommended runtime path uses `llama-server.exe --api-key-file`; key values are not printed or passed in process arguments.
- Metrics are opt-in and omit prompt text, full responses, Bearer values, and key paths.
- Private LAN mode requires gateway auth for model endpoints.

## Validation
- Full local validation passed with 157 tests.
- `release-check --target 0.1.23` reports `ready_for_integration` on the milestone branch.
- Local dogfood proved Qwen2.5-Coder 7B Q4_K_M can serve fixed smoke, code, JSON, and read-only harness plan workflows through the authenticated local path.
