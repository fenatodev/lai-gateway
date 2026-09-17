# PR130 - Local operator runtime

## Objective

Implement `local-operator-runtime/v1` as the first end-to-end governed local
task orchestration path.

The runtime composes existing LAI local-task components instead of introducing
new authority or a general-purpose shell.

The intended chain is:

`local-task/v1`
-> file pack
-> review gate
-> approval gate
-> content binding
-> bounded green executor
-> operator result

## Product goal

PR130 is intended to reduce manual coordination between the local task stages.

A caller should not need to invoke review, approval and executor independently
for a green-zone local task already supported by the bounded executor.

The operator coordinates existing components. It does not become a new policy
engine, authority source or unrestricted execution surface.

## Runtime contract

`local-operator-runtime/v1` must:

- accept one bounded local task request;
- preserve domain, channel, autonomy and capability as separate fields;
- materialize or consume `local-task/v1` through the existing local-task path;
- invoke the existing review gate;
- require the existing approval gate decision;
- preserve `task_digest` across the chain;
- invoke the existing green executor only when the approval result is
  `ready_without_approval`;
- return one structured result describing each stage;
- fail closed if any stage is invalid or blocked;
- execute no command when review, approval or content binding fails.

## Green-zone scope

PR130 may automatically execute only work already permitted by
`local-task-green-executor/v1`.

The PR127 exact command allowlist must remain unchanged.

PR130 must not reinterpret a yellow or red task as green.

Yellow-zone and red-zone tasks must stop before operational execution.

## Authority boundaries

The operator runtime does not:

- grant permission;
- issue or consume grants;
- change autonomy zone;
- widen the green executor allowlist;
- provide arbitrary shell access;
- infer authorization from task, memory, files, code, web, tools or model output;
- call Harness for ordinary local-task execution;
- dispatch adapters or external tools;
- use credentials;
- use authenticated browser state;
- send messages;
- publish;
- submit forms;
- make purchases;
- merge to `main`;
- install or remove software;
- use `sudo`.

Skills, adapters and channels remain capability surfaces, not authority sources.

## Harness boundary

PR130 does not replace the Harness.

Normal `@lai` conversation remains conversation-first and does not create a
Harness run.

Development execution requiring Harness sandbox/review/apply remains a separate
governed path for later integration.

## Filesystem boundary

The runtime must preserve repository-relative bounded paths used by the existing
local task components.

It must not scan `$HOME`, broaden filesystem access, follow implicit project
roots or infer new allowed paths.

## Result model

The runtime result should expose enough stage evidence to diagnose failures
without requiring the caller to manually inspect every intermediate command.

At minimum it should report:

- schema version;
- overall decision;
- task id;
- task digest when available;
- task/file-pack status;
- review status;
- approval status;
- executor status;
- planned commands;
- command results;
- whether commands actually executed;
- security boundary flags.

## Failure semantics

Any of the following must prevent execution:

- malformed task input;
- invalid file-pack output;
- review `invalid` or `blocked`;
- approval result other than `ready_without_approval`;
- missing or malformed `task_digest`;
- digest mismatch;
- non-green autonomy zone;
- human approval requirement;
- command outside the existing exact allowlist;
- command not declared by the task;
- unsafe authority claims.

The runtime must not attempt to repair or override these failures automatically.

## Tests

PR130 must include tests proving at least:

1. valid green task traverses the full chain;
2. successful execution returns stage evidence;
3. yellow task stops before execution;
4. red task stops before execution;
5. mutated task fails content binding;
6. malformed approval or digest executes nothing;
7. non-allowlisted command remains blocked;
8. PR127 exact command allowlist is unchanged;
9. no Harness, adapter, credential, messaging, publication or merge capability
   is introduced.

## Non-goals

PR130 does not:

- expand command coverage;
- implement arbitrary project editing;
- implement the Workbench integration;
- implement Harness development orchestration;
- implement external adapters;
- implement browser automation;
- implement n8n execution;
- implement MCP execution;
- automate PR creation;
- automate merge.

Those remain later milestones.

## Acceptance

PR130 is complete when:

- `local-operator-runtime/v1` exists as a runtime module;
- the runtime composes the existing governed local-task chain;
- green tasks already supported by PR127 can traverse the chain end-to-end;
- yellow/red tasks stop without execution;
- content binding remains enforced;
- the PR127 exact allowlist remains byte-for-byte semantically unchanged;
- existing security boundaries remain intact;
- full repository checks pass;
- product documentation reflects the implemented state without overclaiming.
