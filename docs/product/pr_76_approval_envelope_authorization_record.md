# PR 76 - Approval envelope / authorization record

## Objective

Create a small, auditable authorization record shape after policy evaluation.
This does not capture human approval, grant capabilities, persist authority, or execute adapters.

## Scope

- Add an `AuthorizationRecord` data shape.
- Reuse the minimal policy evaluator and its `PermissionDecision` output.
- Expose a read-only CLI command and Gateway endpoint.
- Keep the record non-effective until a later approval-capture PR exists.

## Non-goals

- No adapter invocation.
- No browser, n8n, voice, document, model, MCP, or social automation execution.
- No persistent approval store.
- No cryptographic user signature.
- No capability grant.
- No external side effect.

## Contract

The record contains the policy `evaluation_id`, the `decision_id`, the requested capability,
the adapter boundary, the actor/channel/domain/action tuple, the approval state, and execution flags.

For this PR:

- `approval_captured` is always `false`.
- `effective_authorization` is always `false`.
- `record_persisted` is always `false`.
- `grants_permission` is always `false`.
- `executes_tools` is always `false`.

## Expected behavior

- A `requires_approval` decision produces a `requires_human_approval` authorization record.
- A `deny` decision produces a `blocked` authorization record.
- An `allow` decision may produce `not_required`, but still does not grant execution authority.

## Interfaces

- CLI: `lai-gateway authorization-record --adapter <id> --capability <capability>`
- Endpoint: `GET /v1/gateway/authorization-record`

Both interfaces are read-only and secret-free.
