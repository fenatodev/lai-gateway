# PR124 — local task file pack

## Status

PR124 implements `local-task-file-pack/v1`.

It turns the PR123 dry-run payload into a bounded local task/outbox file plan and, when explicitly requested, writes JSON records under `.lai-ai/tasks` and `.lai-ai/outbox`.

## Scope

PR124 adds:

- `lai_gateway.local_task_file_pack`
- `lai-gateway local-task-file-pack`
- explicit `--write` behavior for bounded JSON records
- tests for plan-only, write, blocked path, red-zone blocking, renderer, and CLI JSON behavior
- product documentation for `local-task-file-pack/v1`

## Non-goals

PR124 does not add real local task execution, shell execution, command execution, Harness calls, tool calls, adapter dispatch, grant issuance, grant consumption, credential access, authenticated browser access, message sending, publication, merge to `main`, or external side effects.

## Behavior

Default behavior is plan-only.

With `--write`, PR124 writes only task/outbox JSON records for a non-blocked local task file pack.

Unsafe output roots are blocked.

Red-zone tasks are blocked and are not written as ready.

## Authorization rule

A local task file pack is never authorization.

Written task files and written outbox files are review artifacts only. They do not grant permission to execute.

## Validation

Expected validation:

- `python3 -m unittest tests.test_local_task_file_pack -v`
- `python3 -m unittest tests.test_product_docs -v`
- `git diff --check`
- `PYTHON=python3 make check`
