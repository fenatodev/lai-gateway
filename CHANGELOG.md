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
