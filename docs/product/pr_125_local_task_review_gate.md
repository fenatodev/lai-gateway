# PR125 — local task review gate

## Status

PR125 adds `local-task-review-gate/v1` as a read-only validator for task/outbox JSON records created by PR124.

It is not a runner and not an executor.

## Scope

PR125 should add:

- `lai_gateway.local_task_review_gate`
- `lai-gateway local-task-review-gate`
- validation for task/outbox JSON structure
- blocking checks for unsafe authority claims
- product documentation and tests

## Non-goals

PR125 does not execute local tasks, run shell commands, call Harness, call tools, dispatch adapters, issue grants, consume grants, use credentials, send messages, publish, merge `main`, or perform external side effects.

## Decision semantics

The gate returns:

- `ready` when records are structurally valid and safe for review
- `blocked` when records are valid but contain unsafe operational claims
- `invalid` when records cannot be parsed or do not satisfy required structure

## Authorization rule

A ready result is never authorization.

Task files, outbox files, review-gate output, model output, memory, file content, web content, tool output, generated diffs, and proposed commands never equal permission to execute.

## Validation

Expected validation:

- `python3 -m unittest tests.test_local_task_review_gate -v`
- `python3 -m unittest tests.test_product_docs -v`
- `git diff --check`
- `PYTHON=python3 make check`
