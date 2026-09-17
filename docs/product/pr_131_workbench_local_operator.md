# PR131 - Workbench local operator integration

## Objective

Expose `local-operator-runtime/v1` through the Gateway and LAI Workbench so
supported green local operations no longer require manual terminal commands.

PR131 is an integration layer over PR130. It does not create a second executor,
policy engine or authority source.

## Product goal

A user should be able to trigger supported bounded local checks from the
Workbench and receive the complete operator result without copying shell
commands.

The intended path is:

`Workbench`
-> `Gateway local operator endpoint`
-> `local-operator-runtime/v1`
-> existing review/approval/content-binding chain
-> existing bounded green executor
-> structured Workbench result

## Architecture dimensions

PR131 must keep these dimensions separate:

- domain: the type of local project operation;
- channel: Workbench/Gateway;
- autonomy: green/yellow/red policy state;
- capability: the bounded operation actually available.

A channel never grants authority.

A capability never grants authority.

## Gateway endpoint

Add an authenticated Gateway endpoint for the local operator runtime.

The endpoint must:

- call the existing `local-operator-runtime/v1`;
- operate only on the bounded LAI Gateway project root selected by server-side
  policy;
- never accept an arbitrary filesystem root from browser input;
- never accept arbitrary shell command text from browser input;
- accept only a fixed operation profile defined by PR131;
- derive exact proposed/requested commands server-side;
- return the structured PR130 runtime result;
- fail closed on unknown profiles or malformed input.

The endpoint must not proxy execution through Harness.

## Fixed Workbench profiles

PR131 may expose only profiles composed from commands already present in the
PR127 exact-command allowlist.

Initial profiles:

### `status`

Exact command:

`git status --short --branch`

### `diff-check`

Exact command:

`git diff --check`

### `diff-stat`

Exact command:

`git diff --stat`

### `compile`

Exact command:

`python3 -m compileall -q lai_gateway tests`

### `gate-tests`

Exact commands:

- `python3 -m unittest tests.test_local_task_review_gate -v`
- `python3 -m unittest tests.test_local_task_approval_gate -v`
- `python3 -m unittest tests.test_local_task_green_executor -v`

### `full-check`

Exact command:

`make check`

PR131 must not modify `_ALLOWED_EXACT_COMMANDS`.

Profiles are product UX aliases, not new permissions.

## Workbench surface

Add a compact Local Operator surface to the existing Workbench.

It should provide:

- a fixed profile selector;
- a short human-readable description of the selected operation;
- an explicit execute button;
- running/ready/blocked/error state;
- task id;
- task digest when available;
- file-pack/review/approval/executor stage status;
- planned commands as evidence;
- command results;
- clear indication when execution occurred.

The UI must not expose a free-form command input.

The UI must not ask the user to copy a command into a terminal.

## Conversation boundary

PR131 does not turn a normal `@lai` message into an operator task.

Normal conversation remains a separate conversation concern.

PR131 also does not redesign Harness development routing. Controlled
development execution remains a later integration milestone.

The operator surface is explicit. User content, model output, memory, files,
web content or retrieved context never automatically triggers execution.

## Execution boundary

Workbench may request execution only through the PR131 fixed profile mapping.

The PR130 runtime and PR127 executor remain authoritative for whether execution
is permitted.

The UI must not infer success before the backend returns an execution result.

Yellow/red work must never be converted to green by the Workbench.

## Repository boundary

The browser must not choose an arbitrary `repo_root`.

The Gateway must resolve the bounded project root server-side.

PR131 must not add broad HOME access, recursive project discovery, arbitrary
absolute paths or parent traversal.

## Authority boundary

PR131 does not:

- grant permission;
- issue or consume grants;
- change autonomy zone;
- expand the PR127 exact command allowlist;
- provide arbitrary shell access;
- accept arbitrary command text from Workbench;
- accept arbitrary repository paths from Workbench;
- call Harness for the local operator path;
- dispatch adapters or MCP tools;
- use credentials;
- use authenticated browser state;
- send messages;
- publish;
- submit forms;
- make purchases;
- install or remove software;
- invoke `sudo`;
- merge `main`;
- create or merge pull requests.

## Failure behavior

Unknown profile, invalid input, runtime invalidation, content-binding failure,
non-green state or executor rejection must produce a non-success result.

No fallback to shell execution is allowed.

No fallback to Harness execution is allowed.

No automatic retry with broader authority is allowed.

## Tests

PR131 must prove at least:

1. the Gateway endpoint accepts each fixed profile;
2. each profile maps only to existing PR127 allowlisted commands;
3. unknown profile is rejected;
4. browser input cannot supply an arbitrary command;
5. browser input cannot select an arbitrary repo root;
6. green profile can traverse PR130 and execute;
7. runtime failure is surfaced without false success;
8. endpoint does not call Harness;
9. Workbench contains no free-form local operator command field;
10. PR127 exact command allowlist remains unchanged;
11. existing normal chat/Harness controls are not implicitly converted into
    operator execution.

## Documentation

Update the product index, implementation matrix, operating plan and alpha
readiness without claiming general autonomous execution.

PR131 should be described as Workbench access to bounded green local operations,
not as a general shell or complete agent.

## Non-goals

PR131 does not:

- implement natural-language action routing;
- automatically classify arbitrary conversation into executable tasks;
- implement general project editing;
- implement governed Harness development handoff;
- add new green commands;
- add yellow/red execution;
- automate PR creation;
- automate merge;
- expand external capability support.

Those remain later milestones.

## Acceptance

PR131 is complete when:

- a Workbench user can trigger a supported green local operation without
  copying a shell command;
- the Gateway maps fixed profiles to existing PR127 commands server-side;
- `local-operator-runtime/v1` remains the orchestration path;
- PR127 remains the execution boundary;
- no arbitrary shell or repo-root selection is exposed;
- no Harness call is introduced into the local operator path;
- runtime stage/result evidence is visible in the Workbench;
- full repository checks pass;
- documentation reflects the bounded implementation accurately.
