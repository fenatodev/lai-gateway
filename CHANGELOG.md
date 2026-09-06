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
