# PR126 — Local task approval gate

## Intent

PR126 adds `local-task-approval-gate/v1`, a read-only approval decision layer after PR125.

It turns a reviewed local task into one of four explicit states:

- `ready_without_approval`
- `needs_approval`
- `blocked`
- `invalid`

## Scope

PR126 may add:

- a Python module for approval-gate collection/rendering
- a CLI command
- focused tests
- product documentation
- product documentation tests

## Boundaries

PR126 must not introduce an executor.

PR126 must not execute shell commands, call Harness, call tools, dispatch adapters, issue grants, consume grants, use credentials, send messages, publish, merge into `main`, or create external effects.

Approval state in PR126 is advisory and non-effective. It is not permission.

## Validation target

Expected local validation:

- `python3 -m unittest tests.test_local_task_approval_gate -v`
- `python3 -m unittest tests.test_product_docs -v`
- `PYTHON=python3 make check`

## Next step

A later PR may introduce a minimal green-zone executor, but only after this approval gate exists and remains non-authorizing by itself.
