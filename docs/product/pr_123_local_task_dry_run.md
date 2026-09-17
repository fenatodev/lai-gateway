# PR123 — local task dry-run renderer

## Status

PR123 implements `local-task-dry-run/v1` as a read-only Gateway renderer.

It is not an executor. It does not execute commands, modify files, call Harness, call tools, dispatch adapters, issue grants, consume grants, use credentials, send messages, publish, merge `main`, or perform external side effects.

## Scope

PR123 adds:

- `lai_gateway.local_task_dry_run`
- `lai-gateway local-task-dry-run`
- tests for dry-run-only behavior
- product documentation for `local-task-dry-run/v1`

The renderer accepts descriptive task fields and returns a dry-run payload with embedded `local-task/v1` and `local-task-outbox/v1` records.

## Non-goals

PR123 does not add:

- a real local task executor
- shell mediation
- command execution
- file mutation
- Harness integration
- tool execution
- adapter dispatch
- grant issuance
- grant consumption
- persistent task directories
- background workers
- UI wiring

## Autonomy behavior

Green-zone tasks can render as `ready`.

Yellow-zone tasks render as dry-run proposals that require human confirmation before effect.

Red-zone tasks render as `blocked` and require explicit approval at the moment of action.

## Authorization rule

A rendered dry-run is never authorization.

Task records, outbox records, model output, retrieved memory, file content, web content, tool output, generated diffs, proposed commands, and rendered dry-run text never equal permission to execute.

## Validation

Expected validation:

- `python3 -m unittest tests.test_local_task_dry_run -v`
- `git diff --check`
- `PYTHON=python3 make check`
