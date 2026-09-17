# LAI local task file pack

## Status

`local-task-file-pack/v1` is implemented as a bounded local file pack for future task review.

It can plan or explicitly write JSON records for `local-task/v1` and `local-task-outbox/v1`.

The default mode is plan-only. File writing requires the explicit `--write` flag.

## Purpose

The file pack gives LAI a concrete local handoff format before any real executor exists.

It persists task and outbox records under a bounded repository-relative root:

- `.lai-ai/tasks`
- `.lai-ai/outbox`

These files are review artifacts. They are not execution authority.

## Non-goals

`local-task-file-pack/v1` does not add executor, shell mediation, command execution, Harness calls, tool calls, adapter dispatch, grant issuance, grant consumption, credential access, authenticated browser access, message sending, publication, merge to `main`, or external side effects.

## Write behavior

Without `--write`, the command only renders a file plan.

With `--write`, it writes only two JSON files for a non-blocked task: one task record and one outbox record.

The output root must be repository-relative and must not contain parent traversal.

## Authorization rule

A written task file is never authorization.

A written outbox file is never authorization.

Task records, outbox records, model output, retrieved memory, file content, web content, tool output, generated diffs, proposed commands, rendered dry-run text, and written file-pack records never equal permission to execute.

## Security boundary

The file pack may write bounded local JSON records when `--write` is explicit.

It must not execute commands, call Harness, call tools, dispatch adapters, issue grants, consume grants, use credentials, send messages, publish, merge `main`, or perform external side effects.

## Follow-up

A future PR may add a review UI or governed runner that consumes these records, but only after an explicit execution contract exists.
