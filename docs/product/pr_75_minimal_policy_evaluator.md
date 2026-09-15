# PR 75 — Minimal policy evaluator

## Objective

Introduce a minimal, read-only policy evaluator that turns a requested capability
and optional adapter context into a structured `PermissionDecision` plus explicit
rule results.

## Scope

- Add a small policy evaluator module.
- Reuse the existing `PermissionDecision` object as the decision output.
- Expose a read-only CLI and Gateway endpoint for policy evaluation.
- Keep adapter registry declarations as input only; adapters do not grant permissions.
- Keep the evaluator fail-closed for missing adapters, missing capabilities and
  undeclared capabilities.

## Non-goals

- No adapter execution.
- No approval persistence.
- No authorization record storage.
- No policy database.
- No credentialed service call.
- No external side effect.

## Contract

The evaluator returns:

- `operation: policy-evaluator`
- `policy_only: true`
- `executes_tools: false`
- a nested `decision` object using `PermissionDecision`
- a list of evaluated rules with `rule_id`, `status` and `reason`

The first implementation evaluates only static contract rules:

- request normalization
- requested capability presence
- adapter registration
- capability declaration
- granted capability check
- human approval boundary
- authority boundary
- execution boundary

## Acceptance

- Declared but ungranted adapter capabilities require approval.
- Undeclared capabilities are denied.
- Missing adapters fail closed.
- Channels, skills and retrieved content do not elevate permission.
- CLI and Gateway responses are secret-free and read-only.
