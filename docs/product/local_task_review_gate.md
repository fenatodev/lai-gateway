# LAI local task review gate

## Status

`local-task-review-gate/v1` is a planned read-only validation gate for local task file-pack artifacts.

It reviews JSON records produced by `local-task-file-pack/v1` before any future runner can consume them.

## Purpose

The review gate exists to prevent a written task file from becoming implicit execution authority.

It checks local task/outbox records and returns a review decision:

- `ready`
- `blocked`
- `invalid`

## Inputs

The gate reviews bounded local JSON files:

- a `local-task/v1` task file
- a `local-task-outbox/v1` outbox file

The files are expected to come from `.lai-ai/tasks` and `.lai-ai/outbox`.

## Required checks

The gate must reject or block:

- missing files
- invalid JSON
- wrong schema versions
- mismatched task ids
- path traversal
- absolute file paths
- red-zone task records
- false authorization claims
- command execution claims
- Harness call claims
- tool call claims
- adapter dispatch claims
- grant issuance claims
- grant consumption claims
- credential usage claims
- message sending claims
- publication claims
- merge-to-main claims
- external side-effect claims

## Authorization rule

Passing the review gate is not authorization.

A ready review means only that the local task/outbox records are structurally safe for review. It does not allow execution.

## Security boundary

`local-task-review-gate/v1` must remain read-only.

It must not execute commands, modify task files, call Harness, call tools, dispatch adapters, issue grants, consume grants, use credentials, send messages, publish, merge `main`, or perform external side effects.

## Follow-up

A future PR may connect this gate to a governed runner, but only after an explicit execution contract and approval path exist.
