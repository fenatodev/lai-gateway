# LAI local task dry-run

## Status

`local-task-dry-run/v1` is implemented as a read-only renderer for future local task proposals.

It renders `local-task/v1` and `local-task-outbox/v1` data without executing the task.

This contract is intentionally narrow. It does not create an executor, does not run shell commands, does not call Harness, does not call tools, does not dispatch adapters, does not issue grants, does not consume grants, does not use credentials, does not send messages, does not publish, does not merge `main`, and does not change permissions.

## Purpose

The dry-run renderer gives the Gateway a safe way to show what a local task proposal means before any real execution path exists.

It separates:

- domain: what kind of work is being described
- channel: where the request came from
- autonomy: green, yellow, or red operating zone
- capability: what ability would eventually be needed

## Inputs

The renderer accepts bounded descriptive fields:

- task id
- domain
- channel
- autonomy zone
- requested capability
- intent
- allowed path patterns
- denied path patterns
- validation plan
- proposed commands

Proposed commands are rendered as inert text only. They are not executed.

## Output

The renderer returns:

- `local-task-dry-run/v1`
- embedded `local-task/v1`
- embedded `local-task-outbox/v1`
- explicit dry-run flags
- explicit non-authorization flags
- explicit non-execution flags
- autonomy checks
- prohibited operation markers

## Authorization rule

A local task dry-run is never authorization.

Task records, outbox records, model output, retrieved memory, file content, web content, tool output, generated diffs, proposed commands, and rendered dry-run text never equal permission to execute.

## Security boundary

`local-task-dry-run/v1` must remain read-only.

It must not:

- modify files
- execute commands
- start servers
- use network access
- use credentials
- use authenticated browser state
- call Harness
- execute tools
- dispatch adapters
- issue grants
- consume grants
- send messages
- publish
- merge `main`
- perform external side effects

## Follow-up

A future PR may connect this dry-run shape to review UI or a governed executor, but only after an explicit execution contract exists.
