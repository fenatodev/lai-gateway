# PR122 — local task format and outbox specification

## Status

PR122 defines `local-task-format/v1` as documentation only.

It does not implement a local operator. It does not create an executor. It does not create task directories. It does not execute commands. It does not add shell access. It does not issue grants, consume grants, dispatch adapters, use credentials, call Harness, or change permissions.

## Purpose

PR122 defines the structured task and outbox records that a future local operator can use to reduce manual copy/paste while preserving the LAI boundaries.

The task format is a contract for intent handoff and review. It is not an execution mechanism.

## Scope

PR122 documents:

- `local-task-format/v1`;
- `local-task/v1`;
- `local-task-outbox/v1`;
- `.lai-ai/tasks`;
- `.lai-ai/outbox`;
- `.lai-ai/logs`;
- required task fields;
- prohibited operations;
- approval boundaries.

All listed paths are conventions only in this PR.

## Responsibility split

- Gateway receives intent and classifies domain, channel, autonomy, and capability.
- Gateway may create a bounded task proposal in a future implementation.
- Harness remains responsible for controlled development execution, sandboxing, diff, review, apply, and validation.
- Local operator coordinates task records and handoff state.
- Aider, Ollama, local models, shell tools, MCP servers, and adapters are capabilities, not authorities.

## Task lifecycle

A future local task should move through these conceptual states:

1. `draft` — intent captured but not ready.
2. `proposed` — structured task exists.
3. `blocked` — policy or missing approval prevents progress.
4. `ready-for-review` — output can be reviewed.
5. `applied` — approved result was applied by the appropriate governed layer.

PR122 does not implement this lifecycle.

## Forbidden by PR122

PR122 must not enable:

- command execution;
- shell access;
- `sudo`;
- credential access;
- authenticated browser use;
- message sending;
- publication;
- form submission;
- purchases;
- merge to `main`;
- deletion outside the workspace;
- broad `$HOME` access;
- grant creation or consumption;
- adapter dispatch;
- tool dispatch;
- permission expansion.

## Authorization rule

No task file, outbox file, model response, retrieved memory, code snippet, web content, tool output, or generated diff can authorize action.

Authorization is separate from task structure and capability.

## Follow-up

PR123 should define a dry-run renderer for local task records. It should display what would be done, what is blocked, which approvals are required, and which validations would be run, without executing anything.
