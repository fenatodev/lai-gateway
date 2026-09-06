## [0.1.0] - 2026-09-06

Initial public companion gateway scaffold.

- Add dependency-free Python gateway client for `lai harness v0.4.2`.
- Add loopback-only gateway server exposing read-only harness contract, status, and readiness routes.
- Add contract validation against the harness gateway contract.
- Add CLI commands for config, contract, status, readiness, serve, and release readiness checks.
- Add CI, Dependabot, branch protection, and minimal source-only release governance.

No remote run creation, Telegram, PWA, public bind, direct llama.cpp proxy, shell authority, or publication automation is exposed in this release.
