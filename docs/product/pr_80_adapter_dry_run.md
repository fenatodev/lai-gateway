# PR 80 - Adapter dry-run

## Goal

Add the first governed adapter dry-run surface.

The dry-run is real Gateway code: it builds the current permission decision,
policy evaluation, authorization record, invocation proposal and audit events,
then produces a deterministic simulated execution result. It does not dispatch
an adapter.

## In scope

- Add a serializable `AdapterDryRun` envelope.
- Add CLI command `adapter-dry-run`.
- Add endpoint `GET /v1/gateway/adapter-dry-run`.
- Reuse the existing proposal and audit-event chain.
- Redact sensitive-looking parameters before output.
- Fail closed for missing adapters and undeclared capabilities.

## Out of scope

- No adapter dispatch.
- No tool execution.
- No network call.
- No filesystem write.
- No credential use.
- No human approval capture.
- No effective authorization.

## Security invariant

Dry-run evidence is useful for planning and UI visibility, but it never grants
permission. Any future real adapter execution must still pass through policy,
authorization capture, persistence and audit gates.
