# lai-gateway v0.1.22 Release Notes

v0.1.22 is the mobile operations completion milestone. It turns the previous mobile preview into a more diagnosable daily-use flow, while keeping the gateway deliberately conservative.

## Added
- `lai-gateway ops-status` for a single read-only operational snapshot.
- `lai-gateway mobile-repair` for pair-token refresh and bridge planning/repair.
- `lai-gateway service-plan`, `service-install`, and `service-remove` for token-free systemd-user service management.
- `lai-gateway-mobile`, an idempotent fallback launcher for environments where user systemd is unavailable.
- `lai-gateway model-status` plus `/v1/gateway/model-status` for local model runtime readiness.
- `lai-gateway model-plan` plus `/v1/gateway/model-plan` for safe runtime preparation guidance.
- Operations and Model panels in the local UI.
- `docs/MOBILE_OPS.md` and `docs/MODEL_OPS.md` runbooks.

## Changed
- `ops-status` now includes local model readiness.
- Installed wrappers pin the repository directory correctly.
- Mobile repair/status JSON avoids bulky QR SVG fields unless needed.
- Service diagnostics distinguish a present `systemctl` binary from an actually usable `systemd --user` bus.

## Security
- Ops, model, service, and repair diagnostics remain token-free and read-only by default.
- Private LAN mode requires gateway auth for `ops-status`, `model-status`, and `model-plan` endpoints.
- `model-status --probe-openai` only probes safe local/private HTTP endpoints with explicit ports.
- No public bind, shell authority, write-capable runs, direct model proxy, model API key exposure, automatic model downloads, or automatic tunnel setup is introduced.

## Validation
- Full local validation passed with 125 tests.
- `release-check --target 0.1.22` reports `ready_for_integration` on the milestone branch.
