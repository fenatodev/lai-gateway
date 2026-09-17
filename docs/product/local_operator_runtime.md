# LAI local operator runtime

## Status

`local-operator-runtime/v1` is implemented by PR130.

It composes the existing governed local-task pipeline. It does not introduce a
new authority source, arbitrary shell, new command allowlist entries or external
capabilities.

## Purpose

The runtime reduces manual coordination between the local task stages.

For a bounded task it coordinates:

`local-task-file-pack/v1`
-> `local-task-review-gate/v1`
-> `local-task-approval-gate/v1`
-> `local-task-green-executor/v1`

Content identity remains bound by `local-task-content-binding/v1`.

## Execution boundary

Only an existing green-zone task that reaches
`ready_without_approval` may reach the bounded green executor.

The runtime does not reinterpret yellow or red work as green.

Yellow work stops at `needs_approval`.

Red or invalid work stops before execution.

## Command boundary

PR130 does not add commands to the PR127 exact allowlist.

The executor remains responsible for:

- exact argv allowlisting;
- task-declared command checks;
- blocked-token checks;
- `shell=False`;
- command count limits;
- content digest verification.

The operator runtime only composes those existing checks.

## Authority boundary

The runtime does not:

- grant permission;
- issue or consume grants;
- change autonomy zone;
- infer authorization from content;
- call Harness for this local task path;
- dispatch adapters;
- execute external tools;
- use credentials;
- use authenticated browser state;
- send messages;
- publish;
- submit forms;
- purchase;
- merge `main`;
- install software;
- invoke `sudo`.

Domain, channel, autonomy and capability remain separate task fields.

## Filesystem behavior

The runtime may materialize the existing bounded task/outbox artifacts under the
explicit repository-relative local-task output root.

That metadata write does not authorize source changes.

No broad HOME scan or implicit project-root discovery is introduced.

## Content binding

The review gate computes the canonical `task_digest`.

The approval gate requires and propagates that digest.

The executor recomputes the digest from the exact parsed task used for command
checks.

Any missing, malformed or mismatched digest fails closed before execution.

## Harness boundary

PR130 does not replace the Harness.

Normal `@lai` conversation remains conversation-first.

Controlled development sandbox, diff, review and apply remain Harness
responsibilities and require their own later integration.

## User-visible result

The runtime returns one structured result with:

- task identity;
- content digest;
- stage status;
- planned commands;
- command results;
- whether execution occurred;
- security-boundary flags.

This reduces the need to invoke each local task stage manually.

## Limits

PR130 does not yet connect this runtime to the Workbench conversation path.

It also does not provide general project editing, arbitrary shell, automatic PR
creation, automatic merge or external automation.

Those are separate milestones.
