# Workbench local operator

## Status

`workbench-local-operator/v1` is implemented by PR131.

It exposes a bounded Workbench/Gateway surface over
`local-operator-runtime/v1`.

The browser does not receive an arbitrary shell interface.

## Purpose

PR131 removes terminal copy/paste for a narrow set of already-authorized green
local validation operations.

The user chooses a fixed operation profile in the Workbench.

The browser sends only the profile identifier.

The Gateway maps that identifier to exact commands already present in the PR127
green executor allowlist.

## Profiles

The initial profiles are:

- `status`
- `diff-check`
- `diff-stat`
- `compile`
- `gate-tests`
- `full-check`

These profiles are UX aliases only. They are not permissions.

## Request boundary

The Workbench request contains only:

`profile`

It does not contain:

- arbitrary command text;
- arbitrary argv;
- arbitrary repository root;
- autonomy override;
- execution policy override;
- Harness run parameters;
- credentials;
- adapter selection.

The repository root is resolved server-side for the current LAI Gateway source
checkout.

## Runtime path

The path is:

`Workbench`
-> `Gateway`
-> `workbench-local-operator/v1`
-> `local-operator-runtime/v1`
-> file pack
-> review
-> approval
-> content binding
-> green executor

The Gateway does not bypass PR130 or PR127.

## Filesystem behavior

PR131 writes local task metadata under:

`state/local-operator`

The existing repository ignore policy already excludes `state/`.

This prevents normal Workbench operator runs from dirtying the source checkout
with task metadata.

Source modification is not introduced by PR131.

## Authority

PR131 does not:

- grant authority;
- change autonomy;
- issue or consume grants;
- expand the green executor allowlist;
- provide arbitrary shell;
- call Harness for the operator path;
- dispatch adapters or MCP tools;
- use credentials;
- send messages;
- publish;
- submit forms;
- purchase;
- install software;
- invoke sudo;
- create pull requests;
- merge main.

Domain, channel, autonomy and capability remain separate concepts.

## Conversation boundary

Normal `@lai` conversation remains direct conversation.

A chat message does not automatically become an operator execution.

The Workbench operator is an explicit control surface.

Natural-language routing into governed execution remains a later milestone.

## UI evidence

The Workbench shows:

- selected profile;
- execution status;
- task id;
- task digest;
- file-pack stage;
- review stage;
- approval stage;
- executor stage;
- planned commands;
- command results;
- whether execution occurred.

Backend result determines success. The UI does not infer success locally.

## Limitations

PR131 does not provide general development autonomy.

It does not edit arbitrary source files, create branches, commit, push, open PRs
or call Harness development workflows.

Its purpose is narrower: remove copy/paste for bounded green local operations
already supported by the existing executor.
