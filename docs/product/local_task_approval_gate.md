# LAI local task approval gate

## Status

Implemented by PR126.

`local-task-approval-gate/v1` is a read-only approval decision layer for local task records that have already passed `local-task-review-gate/v1`.

It does not execute tasks. It does not grant permission. It does not consume grants. It does not call the Harness, shell, tools, adapters, browser automation, n8n, credentials, messaging, publication, or merge operations.

## Purpose

The approval gate separates four states:

- `ready_without_approval`: safe green-zone task that may proceed to a future governed executor.
- `needs_approval`: yellow-zone task or task with proposed effects that requires explicit human approval before execution.
- `blocked`: red-zone task or task containing unsafe authority claims.
- `invalid`: malformed input, missing review result, schema mismatch, or inconsistent task/outbox identity.

## Inputs

The gate accepts review output from `local-task-review-gate/v1`.

The review output is treated as untrusted content until validated.

Required properties:

- `schema_version`
- `overall`
- `decision`
- `task_id`
- `read_only`
- `effective_authorization`
- `executes_commands`
- `calls_harness`
- `executes_tools`
- `dispatches_adapter`
- `issues_grants`
- `consumes_grants`
- `uses_credentials`
- `sends_messages`
- `publishes`
- `merges_main`
- `external_side_effects`
- `checks`

## Decision rules

The gate must return `invalid` when the review payload is malformed or not `local-task-review-gate/v1`.

The gate must return `blocked` when the review decision is `blocked`, when the review exposes unsafe authority claims, or when any red-zone indicator is present.

The gate must return `needs_approval` when the review is structurally valid but the task is not safe for automatic green-zone execution.

The gate may return `ready_without_approval` only when the review is valid, ready, read-only, non-authorizing, non-executing, non-dispatching, non-publishing, non-merging, free of external side effects, and carries explicit green-zone evidence.

## Non-goals

PR126 must not:

- execute commands
- start a shell
- call the Harness
- call tools
- dispatch adapters
- issue grants
- consume grants
- use credentials
- send messages
- publish
- merge into `main`
- modify task/outbox files
- produce external side effects
