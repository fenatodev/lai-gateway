## [Unreleased]

### Fixed
- Make `model-smoke` use an explicit local connectivity health-check prompt so the validated Ministral baseline returns the fixed marker instead of refusing a bare marker request.
- Persist token-free model runtime config from `scripts/launch-model.sh` and let `ops-status` run the safe local model probe so later checks can see the active endpoint without re-exporting environment variables.
- Make `scripts/launch-model.sh --create-key` idempotently reuse an existing valid key file unless `--force-key` is explicitly requested.
- Keep `scripts/stack-check.sh` focused on Gateway/Harness compatibility by tolerating release-readiness-only `main_sync` and `tag_state` failures on post-release development branches.
- Suppress mobile bridge/proxy guidance from `ops-status` once the mobile path is already ready, so a ready daily stack does not still print repair-style next steps.

## [0.1.34] - 2026-09-07

### Changed
- Add `AGENTS.md` and `docs/OPERATING-MODE.md` to codify the Gateway product-progress decision gate, local-first milestone batching, and capability-based Harness compatibility policy.
- Replace patch-exact Harness targeting with a default minimum Harness 0.4.6 plus contract/capability validation, while retaining `--target-harness` for exact release audits.
- Refresh current stack documentation and test fixtures for the Harness v0.4.7 verified baseline without requiring future Gateway releases for compatible Harness patch bumps.

### Validation
- Stack-check defaults must pass against installed `lai-gateway` 0.1.34 and any compatible `lai harness` >=0.4.6 exposing the required contract/capabilities; Harness 0.4.7 is the verified baseline.

## [0.1.33] - 2026-09-07

### Added
- Add a Gateway UI run timeline panel that reads `GET /v1/harness/runs/{control_run_id}/events` and displays metadata-only progress while a selected run is polled.

### Changed
- Keep read-only run polling focused on status plus sanitized event metadata, without adding write modes, browser automation, MCP execution, or persistent token storage.

## [0.1.32] - 2026-09-07

### Added
- Add read-only Harness run-event timeline support with `lai-gateway runs events <control_run_id>` and `GET /v1/harness/runs/{control_run_id}/events`.
- Sanitize run-event payloads defensively so stdout, stderr, task text, turns, and transcripts are stripped before reaching CLI or Gateway API clients.

### Changed
- Update the default Gateway/Harness stack target to `lai harness` 0.4.6 and bump the Gateway package to 0.1.32.

## [0.1.31] - 2026-09-07

### Added
- Add Gateway proxy support for the Harness 0.4.5 MCP broker foundation: `lai-gateway mcp status`, `lai-gateway mcp tools`, `lai-gateway mcp policy-check`, and `/v1/harness/mcp/*`.
- Surface `mcp_broker` in `ops-status` so daily diagnostics include the MCP foundation state.
- Add MCP-focused coverage for the harness client, contract validation, CLI, server proxy, private-mode auth, and ops status rendering.
- Add `scripts/stack-check.sh`, the `lai-gateway-stack-check` wrapper, and `make milestone-gate` for local Gateway/Harness compatibility validation before commit or publication, with human-readable and `--json` output that works from any current directory.
- Add `scripts/publication-scan.sh` and wire it into `make check` to block private local path, known local IP, or blocked release-prose leakage from public release surfaces.
- Harden `.gitignore` for local private/runtime/build artifacts, with regression coverage for caches, logs, keys, VSIX, SQLite, GGUF, and `.secrets/`.
- Declare explicit setuptools build metadata and package discovery in `pyproject.toml`, with regression coverage for the build backend, console script, `lai_gateway*` package inclusion, test/docs/scripts exclusion, and static UI package data.

### Changed
- Expose top-level `validation_command` and `validation_commands` fields in `release-check --json` while retaining the compatibility check entry for existing parsers.
- Strengthen the stack compatibility gate to require the release-check JSON validation command fields used by automation.
- Align fake-harness persistent-session delete fixtures and tests with the real Harness `session.deleted` response shape.
- Dogfood installed private HTTP Gateway session-bound read-only run creation, polling, list lookup, session persistence, and deletion against a real temporary `lai serve` Harness.
- Align fake-harness run IDs with the real `cr-<16 hex>` control-run shape.
- Normalize legacy Harness run-list records that expose `run_id` by adding `control_run_id` for Gateway CLI/UI compatibility.
- Validate control-run and control-session identifiers against the Harness `cr-<16 hex>` and `cs-<16 hex>` shapes before proxying run/session requests.
- Require every Harness run/session route used by the Gateway in contract validation, including list and read endpoints, not only create/delete.
- Make `lai-gateway release-check --json` resolve the Gateway checkout when the installed wrapper is launched from outside the repository.
- Centralize HTTP request-body parsing with `_read_body` and `_read_json_object`, then reuse it for read-only run creation and MCP policy checks.
- Update Gateway contract fixtures and local dogfood expectations to the Harness 0.4.5 MCP contract shape.

### Security
- Preserve the non-executing MCP boundary: `call-tool` policy checks are proxied as classification only, return `executed: false`, and do not expose MCP tool execution through the gateway.
- Dogfood installed `lai-gateway` session lifecycle against a real temporary `lai serve` Harness, using temporary token/data homes and redacted session evidence.
- Dogfood installed private HTTP Gateway session lifecycle against a real temporary `lai serve`, confirming static UI access, protected `/v1/harness/*` auth, and `session.deleted` delete evidence.
- Defensively redact secret-shaped fields from MCP status/tool/policy payloads before they reach CLI, API, UI, ops-status, or Telegram surfaces.
- Replace local machine-specific documentation paths, IPs, and blocked release-prose phrases with generic checkout examples.
- Generalize Windows/WSL model discovery roots instead of shipping a machine-specific user profile path.

## [0.1.30] - 2026-09-06

- Added mobile session exchange so short-lived pair tokens unlock longer page-memory sessions without storing permanent tokens on the phone. Pair tokens are now accepted only for session exchange, not direct protected API access; forgetting a mobile session revokes it from server memory.
- Prefer the validated Ministral baseline in local GGUF model discovery when it is available, after Qwen2.5-Coder dogfood failed to become decision-eligible for the LAI workflow.
- Proxy the Harness session lifecycle delete route through CLI, API, and UI with `lai-gateway sessions delete <session_id>` and `DELETE /v1/harness/sessions/{session_id}`.
- Refuse `--show-pair` in non-interactive launcher output so pair tokens are not accidentally written to `nohup`, pipe, or log files.

## [0.1.29] - 2026-09-06

- Added `daily-config` for storing the local daily mobile IP, phone URL, proxy port, and harness repo without tokens.
- Updated `lai-gateway-daily` to load safe persisted daily defaults so routine startup can run without repeating IP and URL arguments.

## [0.1.28] - 2026-09-06

- Add `lai-gateway-daily` to orchestrate the published daily local workflow: model/Harness readiness, private mobile gateway, loopback mobile proxy, and ops status without printing secrets.

## [0.1.27] - 2026-09-06

### Fixed
- Teach `mobile-proxy --check` to report `ready` when the loopback proxy is already running and serving HTTP, instead of treating the occupied listen port as blocked.

## [0.1.26] - 2026-09-06

### Added
- Add `lai-gateway mobile-proxy` for a loopback-only WSL proxy used by Tailscale Serve to reach the private mobile gateway without relying on a `/tmp` helper script.

### Security
- Keep the mobile proxy transport-only: it does not read, print, store, or validate gateway, pair, Telegram, Harness, or model tokens. Gateway auth remains enforced by the mobile gateway itself.

## [0.1.25] - 2026-09-06

### Changed
- Improve mobile-first gateway UI layout so phone screens no longer widen around large JSON/preformatted output.
- Validate pair tokens immediately from the Gateway access card and show clear success, invalid, expired, or rate-limited feedback.
- Avoid auto-loading protected panels on non-loopback phone access before pairing, preventing repeated `gateway_auth_required` output noise.
- Add the missing model status pill used by model actions.

## [0.1.24] - 2026-09-06

### Changed
- Let `lai-gateway telegram notify-mobile` accept `--candidate-ip` so Telegram mobile notifications can use the same WSL/private target as `mobile-status`, `mobile-repair`, and `mobile-serve`.
- Clarify `ops-status` rendering by separating Harness model readiness from the gateway direct model probe.
- Add a daily operations runbook for the published Harness + Gateway + mobile flow.
- Add `mobile-bridge --check` for read-only portproxy, firewall, and TCP reachability diagnostics.

### Security
- Keep Telegram mobile notifications token-free: the message includes only the mobile URL/bridge guidance and never includes pair, gateway, harness, Telegram, or model API secrets.

## [0.1.23] - 2026-09-06

### Added
- Add `json-mini` structured-output task to the fixed local model evaluation suite.
- Raise the Windows llama.cpp launcher/default examples to `--ctx-size 4096` after real harness plan runs exceeded 2048 tokens.
- Show prompt-free model run history in `ops-status` and suggest `lai-gateway-model --eval --record` when no metrics exist.
- Add fixed local model evaluation with `model-eval`, launcher `--eval`, and `/v1/gateway/model-eval`.
- Add prompt-free local model run metrics with `model-smoke --record`, `model-task --record`, `model-runs`, launcher `--record`, and `/v1/gateway/model-runs`.
- Add `lai-gateway-model --task` to run the fixed local code task after model startup and readiness probing.
- Add `lai-gateway model-task --task code-mini` and `/v1/gateway/model-task` for a fixed, bounded local code-generation task probe.
- Add `lai-gateway-model --smoke` to run fixed-prompt completion validation immediately after local runtime startup.
- Add `lai-gateway model-smoke` for fixed-prompt local completion validation with bounded output and secret-free reporting.
- Add `lai-gateway-model` fallback launcher for starting the recommended Windows llama.cpp runtime from WSL with API-key-file auth and readiness probing.
- Add `lai-gateway model-files` to find local GGUF files, group split models, ignore accessory-only files, and recommend the best local code-model candidate.
- Add `lai-gateway model-key-create` and `model-key-check` for secret-free local model API key-file setup.
- Add `/v1/gateway/model-files` and a Model panel action to inspect local model files from the UI.

### Changed
- Align the documented harness baseline with `lai harness v0.4.3`, which hardens Windows/WSL llama.cpp startup and key-file probing.
- Detect Windows `llama-server.exe` and `llama-cli.exe` from WSL and prefer the proven Windows llama.cpp route before Docker.
- Use the WSL default gateway and port `18082` for Windows llama.cpp planning instead of a generic placeholder.
- Teach `model-status --probe-openai` to read `LAI_GATEWAY_MODEL_API_KEY_FILE` and send Authorization only to validated local/private endpoints.

### Security
- Local model tasks remain fixed-template only; no arbitrary prompt route is exposed through the mobile UI/API.
- Recommend `llama-server.exe --api-key-file` with restricted CORS flags for Windows-hosted local model runtime tests.
- Keep model file discovery, key checks, and model probes token-free in CLI/API output.
- Require gateway auth for `/v1/gateway/model-files` in private LAN mode.

## [0.1.22] - 2026-09-06

### Added
- Add `lai-gateway ops-status` for one read-only gateway, mobile, Telegram, and model operations snapshot.
- Add `lai-gateway mobile-repair` to refresh pair tokens and plan/apply bridge repair without starting a server by default.
- Add `lai-gateway service-plan`, `service-install`, and `service-remove` for token-free systemd user service planning and unit management.
- Add `lai-gateway-mobile` as an idempotent fallback launcher when systemd user services are unavailable.
- Add `lai-gateway model-status` and `/v1/gateway/model-status` to inspect local model runtime readiness without downloads or server startup.
- Add `lai-gateway model-plan` and `/v1/gateway/model-plan` to generate safe, non-mutating local model runtime preparation plans.
- Add UI Operations and Model panels for local dashboard visibility.
- Add `docs/MOBILE_OPS.md` and `docs/MODEL_OPS.md` runbooks.

### Changed
- Include model readiness in `ops-status`.
- Make installed `lai-gateway-ui` and `lai-gateway-mobile` wrappers pin the repository directory correctly.
- Compact mobile repair/status JSON by omitting bulky QR SVG fields where they are not needed.
- Detect unavailable `systemd --user` bus separately from the presence of the `systemctl` binary.

### Security
- Keep ops, model, service, and repair diagnostics token-free and read-only by default.
- Require gateway authentication for `ops-status`, `model-status`, and `model-plan` endpoints in private LAN mode.
- Block `model-status --probe-openai` from probing public, credentialed, query-bearing, fragment-bearing, HTTPS, or portless endpoints.
- Continue to avoid public bind, shell authority, write-capable runs, direct llama.cpp proxy exposure, model API key exposure, automatic model downloads, or automatic tunnel setup.

## [0.1.21] - 2026-09-06

### Added
- Add `lai-gateway mobile-status` to inspect mobile listener, token, pairing, phone URL, and bridge readiness without starting servers or mutating files.

### Security
- Keep mobile status output token-free while still reporting whether access and pair-token files are ready, missing, expired, or invalid.

## [0.1.20] - 2026-09-06

### Changed
- Make `lai-gateway mobile-serve` fail before refreshing pair tokens or sending Telegram notifications when the selected mobile bind target already has a listener.

### Security
- Avoid printing a fresh pair token or sending a stale mobile access notification when startup cannot proceed because the target IP/port is already in use.

## [0.1.19] - 2026-09-06

### Added
- Add `lai-gateway telegram bot-info` to identify the configured bot by public username/id without reading messages or exposing the token.
- Add `lai-gateway telegram chat-set` and `telegram chat-check` to persist the discovered Telegram destination in a `0600` file without printing the chat id.

### Changed
- Resolve Telegram destinations from explicit argument, environment, then the persisted chat-id file.
- Print concrete `chat-set` commands from `telegram discover-chat` alongside optional shell exports.
- Preserve safe Telegram API error descriptions and add actionable recovery hints for common failures such as chat-not-found, invalid-token, blocked-bot, and rate-limit responses.

### Security
- Keep `LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1` mandatory even when the chat id is persisted.
- Redact Telegram bot-token-shaped fragments from HTTP error descriptions before surfacing them in CLI errors.

## [0.1.18] - 2026-09-06

### Added
- Add `lai-gateway telegram token-check` with redacted diagnostics for malformed bot-token files.
- Add `lai-gateway telegram token-repair-whitespace` to safely normalize accidental whitespace only when the compact token shape is valid.
- Add `lai-gateway telegram token-set` to write the bot token with `0600` permissions from a hidden prompt or stdin.

### Changed
- Print concrete `export LAI_GATEWAY_TELEGRAM_CHAT_ID='...'` commands from `telegram discover-chat` instead of unsafe `<chat_id>` placeholders.

### Security
- Keep Telegram token setup secret-free: no token values are printed by check, repair, set, preflight, discovery, or notification commands.

## [0.1.17] - 2026-09-06

### Added
- Add `lai-gateway telegram discover-chat` for explicit one-shot `getUpdates` chat-id discovery with message text redacted by default.
- Add `lai-gateway telegram notify-mobile` to send the current mobile access URL and bridge guidance to the configured Telegram chat.
- Add `lai-gateway telegram notify-status` to send a redacted gateway/doctor status summary to Telegram.
- Add `lai-gateway mobile-serve --telegram-notify` for optional startup notification after preparing mobile access.

### Security
- Require `LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE=1` before polling Telegram updates.
- Keep Telegram notifications outbound-only; no webhook, no Telegram-triggered harness runs, and no gateway/pair/harness tokens in notification payloads.

## [0.1.16] - 2026-09-06

### Added
- Add `lai-gateway mobile-bridge` to plan, apply, or remove Windows-to-WSL portproxy/firewall rules for mobile access.
- Surface `lai_bridge_apply` commands in mobile-access and mobile-serve output so WSL/Tailscale setup is less manual.

### Security
- Keep bridge setup token-free: it forwards only the selected Windows/Tailscale IP and port to the WSL gateway bind.
- Validate listen/connect IPs and reject wildcard, loopback, public, multicast, reserved, link-local, and IPv6 bridge targets.

## [0.1.15] - 2026-09-06

Add WSL/Tailscale-aware mobile access discovery, local QR rendering, and safe Telegram outbound scaffolding.

- Add `lai-gateway mobile-access` and `GET /v1/gateway/mobile-access` to report phone URLs, WSL hints, Windows/Tailscale candidates, portproxy commands, and a local SVG QR code.
- Add a Mobile Access card to the UI with QR rendering, copy-mobile-url support, and no token-bearing QR payloads.
- Prefer Tailscale URLs when available, while still marking WSL/Windows portproxy requirements explicitly.
- Add dependency-free QR SVG generation for short local/mobile URLs.
- Add `lai-gateway telegram preflight` and `lai-gateway telegram send-message` with token files kept out of output, outbound-only behavior, and an explicit send-enable flag.
- Cover QR/mobile-access/Telegram behavior with focused tests and preserve no-storage/no-external-asset UI constraints.

No Telegram webhook, public bind, wildcard bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.14] - 2026-09-06

Polish the local UI for phone-sized screens without increasing gateway authority.

- Add a mobile pairing checklist that tracks token, session, and run readiness in page memory.
- Add read-only task presets, a task character counter, stop-polling control, and clear-session control.
- Improve touch targets, small-screen layout, and mobile card density for the LAN phone flow.
- Keep the UI storage-free, CDN-free, and free of harness control token exposure.
- Add tests for the mobile UI checklist, presets, touch layout, and security regressions.

No public bind, wildcard bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.13] - 2026-09-06

Add explicit mobile serving for the private LAN workflow.

- Add `lai-gateway mobile-serve` to prepare gateway/pair tokens and then start the private LAN gateway in foreground.
- Keep serving explicit: the command still requires a concrete private candidate when autodetection is ambiguous.
- Validate the selected LAN candidate before creating or refreshing token files.
- Keep pair-token output hidden by default; `--show-pair` is explicit for one-time phone pairing.
- Add tests for private config preparation, ambiguous-candidate fail-closed behavior, and missing-harness fail-closed CLI behavior.

No public bind, wildcard bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.12] - 2026-09-06

Add guided mobile startup planning without automatically opening a private bind.

- Add `lai-gateway mobile-start` to combine LAN discovery, token status, pair-token status, mobile URL, and the exact private gateway command.
- Keep `mobile-start` read-only by default; `--prepare` is required before token files are created or refreshed.
- Add explicit `--show-pair` for printing a temporary pair token, and reject it without `--prepare`.
- Add `--candidate-ip` overrides for `lan-info` and `mobile-start` so users and tests can avoid fragile network autodetection.
- Cover the guided mobile flow with deterministic tests that avoid leaking token values.

No public bind, automatic server startup, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.11] - 2026-09-06

Add safe LAN discovery instructions for mobile access.

- Add `lai-gateway lan-info` to discover private LAN IP candidates without starting a server.
- Print mobile UI URLs and exact private-bind startup commands for each candidate.
- Keep the command read-only: no token creation, no server startup, no file mutation, and no remote bind.
- Filter out loopback, wildcard, public, reserved, multicast, and link-local addresses.
- Add tests for LAN candidate filtering, CLI JSON output, secret-free rendering, and shell-safe commands.

No public bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.10] - 2026-09-06

Add a safer pairing experience to the local gateway UI.

- Add token type selection for permanent gateway tokens versus short-lived pair tokens.
- Add optional pairing expiration input and in-memory countdown in the browser.
- Add explicit refresh and forget controls for pairing state.
- Report private API authentication status for success, missing token, rejected token, and rate limiting.
- Keep token values only in page memory with no browser storage, CDN, external URLs, or harness token exposure.

No public bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.9] - 2026-09-06

Add short-lived mobile pairing tokens for private gateway access.

- Add `lai-gateway pair create/check/revoke` for temporary private API pairing.
- Store pairing tokens in a separate `0600` JSON file with an expiration timestamp.
- Let the server accept either the permanent gateway token or a currently valid pairing token in private mode.
- Keep pairing token values hidden by default; `--show` is explicit for one-time phone pairing.
- Add doctor reporting for valid pairing files without exposing token values.

No public bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, persistent browser storage, or automatic tunnel setup is exposed in this release.

## [0.1.8] - 2026-09-06

Harden private LAN setup for mobile access.

- Add `lai-gateway token create` and `lai-gateway token check` for the separate gateway access token.
- Create gateway access tokens with `0600` permissions and avoid printing token values by default.
- Require `0600` gateway token files in private mode.
- Add doctor reporting for gateway access token permissions.
- Add in-memory rate limiting for repeated failed private API authentication attempts.
- Document safer phone/LAN setup without exposing the harness control token to the browser.

No public bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, or automatic tunnel setup is exposed in this release.

## [0.1.7] - 2026-09-06

Add an explicit private LAN binding preview with gateway-side authentication.

- Keep loopback as the default bind mode.
- Allow concrete private IP binds only when `LAI_GATEWAY_PRIVATE_BIND=1` is set.
- Reject wildcard, public, reserved, multicast, and hostname private binds.
- Add a separate gateway access token file for private mode.
- Require gateway bearer authentication for `/v1/harness/*` in private mode while keeping the harness control token server-side.
- Add UI support for a gateway token held only in page memory, plus tests for 401/403/200 private API behavior.

No public bind, harness token exposure to the browser, write-capable runs, shell authority, direct llama.cpp proxy, or automatic tunnel setup is exposed in this release.

## [0.1.6] - 2026-09-06

Add a single-command checked local dev stack.

- Add `python3 -m lai_gateway dev` to run doctor, print the local UI URL, optionally open the browser, and serve the gateway in foreground.
- Keep dev serving loopback-only and reject startup when harness connectivity or contract checks are blocked.
- Route `scripts/launch-local.sh` through the checked `dev` command instead of duplicating launch logic.
- Add tests for blocked dev startup, checked launcher startup, script wrappers, and secret-free output.

No public bind, write-capable runs, shell authority, direct llama.cpp proxy, token exposure, or automatic harness startup is exposed in this release.

## [0.1.5] - 2026-09-06

Add local operational tooling for installing and diagnosing the gateway.

- Add `python3 -m lai_gateway doctor` with JSON and text output for config, token, harness status, readiness, and contract checks.
- Add `python3 -m lai_gateway open-ui --print-only` for deterministic local UI discovery.
- Add `scripts/install-local.sh` to install checkout-backed wrappers in a chosen local bin directory.
- Add `scripts/launch-local.sh` to print/open the UI URL and run the gateway in foreground.
- Add shell syntax checks and tests for doctor, launcher, local install wrappers, and secret-free output.

No public bind, write-capable runs, shell authority, direct llama.cpp proxy, token exposure, or source checkout mutation is exposed in this release.

## [0.1.4] - 2026-09-06

Polish the local gateway UI for read-only operation.

- Add runtime summary pills for readiness, active session, and active run status.
- Add automatic polling after read-only run creation and manual polling for selected runs.
- Add an in-memory compact recent run history with clickable run selection.
- Add output copy support without exposing the harness control token to the browser.
- Keep UI assets local-only with no browser storage, CDN, analytics, or raw harness proxy expansion.

No public bind, write-capable runs, shell authority, direct llama.cpp proxy, or source checkout mutation is exposed in this release.

## [0.1.3] - 2026-09-06

Add a local browser UI for the private gateway.

- Serve a dependency-free local UI at `/`.
- Add static assets for status, readiness, sessions, and read-only run workflows.
- Add security headers, CSP, no-store caching, nosniff, and no-referrer headers to gateway responses.
- Keep token handling server-side; the browser never receives the LAI control token.
- Add tests for local UI routing, static assets, CSP, token absence, and no browser storage usage.

No public bind, authentication bypass, write-mode run creation, shell authority, direct llama.cpp proxy, or external asset loading is exposed in this release.

## [0.1.2] - 2026-09-06

Add read-only harness run creation through the private gateway.

- Add gateway CLI commands for listing, creating, and reading harness runs.
- Add loopback-only HTTP routes for `/v1/harness/runs`.
- Allow only read-only modes: `diagnose`, `plan`, `release`, `review`, and `security`.
- Keep write-capable modes blocked at the gateway boundary.
- Keep raw `POST /v1/runs` blocked to avoid exposing the harness API as an unshaped proxy.
- Add tests for malformed run bodies, write-mode rejection, token redaction, and read-only run proxying.

No public bind, shell authority, direct llama.cpp proxy, or source checkout mutation is exposed in this release.

## [0.1.1] - 2026-09-06

Add session discovery and creation through the private gateway.

- Add gateway CLI commands for listing, creating, and reading harness sessions.
- Add loopback-only HTTP routes for `/v1/harness/sessions`.
- Keep run creation blocked at the gateway boundary.
- Add tests for session proxying, invalid limits, rejected request bodies, and token redaction.

No remote run creation, public bind, shell authority, direct llama.cpp proxy, or source checkout mutation is exposed in this release.

## [0.1.0] - 2026-09-06

Initial public companion gateway scaffold.

- Add dependency-free Python gateway client for `lai harness v0.4.2`.
- Add loopback-only gateway server exposing read-only harness contract, status, and readiness routes.
- Add contract validation against the harness gateway contract.
- Add CLI commands for config, contract, status, readiness, serve, and release readiness checks.
- Add CI, Dependabot, branch protection, and minimal source-only release governance.

No remote run creation, Telegram, PWA, public bind, direct llama.cpp proxy, shell authority, or publication automation is exposed in this release.
