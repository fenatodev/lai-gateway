# PR127 — Local task green executor

PR127 adds `local-task-green-executor/v1`.

The purpose is to introduce the first executable local task step without turning LAI into a general shell runner.

## Scope

Implemented:

- read approval gate output from PR126;
- read local task file from PR124/PR123;
- require `ready_without_approval`;
- require green-zone task metadata;
- require no human approval;
- require command membership in task `proposed_commands`;
- require exact executor allowlist membership;
- run via argv only through `tool_mediation.run_process`, without shell strings;
- expose machine-readable JSON and text rendering;
- document product limits and matrix state;
- test green execution and blocked cases.

Not implemented:

- arbitrary shell;
- command templates;
- file patch application;
- Harness calls;
- adapter dispatch;
- tool execution;
- credentials;
- messages;
- publication;
- merge;
- browser automation;
- n8n execution;
- permission grants.

## Acceptance

PR127 is acceptable only if:

- yellow/red tasks are blocked;
- approval-required tasks are blocked;
- missing or mismatched approval/task identity is invalid;
- non-task-declared commands are blocked;
- non-allowlisted commands are blocked;
- the executor can run at least one green allowlisted command;
- full repo checks remain green.
