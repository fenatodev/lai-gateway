# LAI local task format

## Status

`local-task-format/v1` is a product and architecture specification. PR122 is documentation only.

This document does not create an executor, does not run commands, does not add a shell, does not issue grants, does not consume grants, and does not change permissions.

## Objective

The local task format defines the structured data contract for future LAI local operator tasks.

A local task is a proposal and handoff record. It is not authorization and it is not execution.

## Non-goals

PR122 does not:

- create `.lai-ai/tasks`, `.lai-ai/outbox`, or `.lai-ai/logs` on disk;
- implement a runner;
- execute commands;
- add shell access;
- call aider, Ollama, browser automation, n8n, MCP, adapters, Harness, or tools;
- issue or consume grants;
- change permissions;
- approve actions;
- merge to `main`;
- send messages, publish, submit forms, buy anything, or use credentials.

## Path convention

A future implementation may use these paths inside a bounded project workspace:

- `.lai-ai/tasks/` for task input records;
- `.lai-ai/outbox/` for proposed results and handoff records;
- `.lai-ai/logs/` for audit summaries.

PR122 documents the convention only. It does not create these directories and does not grant write access.

## Local task record

A `local-task/v1` record should identify schema, task id, repository, workspace, domain, channel, autonomy zone, requested capability, intent, allowed paths, denied paths, validation plan, expected outputs, and approval requirement.

The task record is data. It is not permission to execute.

## Outbox record

A future `local-task-outbox/v1` record should summarize status, changed paths, validation results, review state, required approval, and next action.

The outbox is a handoff surface. It is not a permission source.

## Authorization rule

A local task, outbox entry, model response, file, tool output, retrieved memory, web result, or generated diff never equals authorization.

Authorization must be explicit and must be evaluated separately from capability.

## Acceptance criteria

PR122 is acceptable when the repository documents:

- `local-task-format/v1`;
- `local-task/v1`;
- `local-task-outbox/v1`;
- `.lai-ai/tasks`, `.lai-ai/outbox`, and `.lai-ai/logs` as documented conventions only;
- required fields for local task records;
- outbox records as handoff, not authorization;
- no executor, shell, command execution, grants, credential use, or permission change.

## Follow-up

A later PR may add a dry-run renderer for task records. Any implementation must preserve gateway classification, Harness-controlled execution, explicit review, and human approval boundaries.
