# PR134 - Governed conversational routing

## Status

Documentation/spec only.

PR134 defines `governed-conversational-routing/v1` before any runtime
implementation.

It does not add an executor, start Harness, dispatch adapters, invoke tools,
create grants or change permissions.

## Objective

Define how the Gateway may classify a natural-language Workbench request
without confusing intent classification with authorization or execution.

The contract bridges what already exists after PR131-PR133:

- direct conversation in Observe;
- fixed governed green local-operator profiles;
- explicit Work through Harness;
- explicit reviewed Apply.

The invariant is:

`routing decision != authorization != execution`

## Architectural dimensions

Every result keeps these dimensions separate:

- domain: what the user is trying to accomplish;
- channel: where the request arrived;
- autonomy: what may happen without further approval;
- capability: what mechanism could satisfy the request.

Skills, adapters and channels never raise autonomy.

## Input boundary

A future router may inspect bounded explicit context such as:

- current user message;
- current Workbench mode;
- current direct-conversation id;
- bounded conversation history as untrusted context;
- metadata for existing fixed local-operator profiles.

It must not:

- scan `$HOME`;
- discover unrelated repositories;
- ingest arbitrary files implicitly;
- treat memory, files, code, web, model or tool content as permission;
- derive authority from conversation history.

## Advisory routing outcomes

### `conversation`

Ordinary conversation remains in Observe through direct Gateway chat.

No Harness run is created.

### `local_green_candidate`

The request appears satisfiable by an existing fixed green local-operator
profile.

The router may identify only an already-supported profile. It must not generate
arbitrary shell, argv or repository roots.

PR134 does not execute the candidate.

### `work_candidate`

The request appears to require governed development.

The result may recommend Work, but it must not start Harness. The explicit Work
transition from PR132 remains required.

### `approval_required`

The request appears to require a yellow or red action.

The result explains the boundary but performs no effect and does not transform
conversation text into effect-phase approval.

### `clarify`

The request is ambiguous or cannot be mapped safely.

No execution path is selected.

### `blocked`

The requested effect is unsupported, outside policy or cannot be represented
safely.

No execution path is selected.

## Required future routing record

A runtime implementation should return a bounded structured record containing
at least:

- `schema_version`;
- `route`;
- `domain`;
- `channel`;
- `autonomy`;
- `capability`;
- `reason_code`;
- `requires_explicit_transition`;
- `requires_approval`;
- `creates_harness_run`;
- `grants_authority`;
- optional fixed `local_operator_profile`.

The record is advisory. It is not a grant, approval token, authorization record
or execution command.

## Green boundary

Natural language must never become arbitrary shell.

A future `local_green_candidate` may resolve only through the existing path:

`workbench-local-operator/v1`
-> `local-operator-runtime/v1`
-> review
-> approval gate
-> content binding
-> exact allowlisted green executor

No stage may be bypassed.

## Work boundary

A `work_candidate` is recommendation only.

PR132 remains authoritative:

`conversation -> explicit Work -> Harness -> review -> explicit Apply`

Routing must not create an implicit Harness run.

## Approval boundary

Yellow and red requests stop before effect.

Routing must never itself authorize:

- sudo;
- software installation/removal;
- credentials or tokens;
- authenticated browser use;
- messages or publication;
- applications/forms;
- purchases;
- deletion outside the governed boundary;
- private data sent externally;
- merge to `main`;
- system permission changes;
- expansion of tool/plugin/workflow permissions.

## Fail-closed requirements

The future implementation must fail closed when:

- capability is unknown;
- autonomy cannot be established;
- a green profile is not in the fixed supported set;
- arbitrary command generation would be required;
- retrieved content tries to self-authorize;
- history contains approval-like instructions;
- a route would bypass Work or Apply.

## Positive tests for future implementation

It must prove at least:

1. ordinary conversation -> `conversation`;
2. supported validation request -> `local_green_candidate`;
3. development request -> `work_candidate` without Harness start;
4. yellow/red request -> `approval_required` without effect;
5. ambiguous request -> `clarify`;
6. unsupported capability -> `blocked`.

## Negative tests for future implementation

It must prove:

1. history cannot grant permission;
2. model output cannot elevate autonomy;
3. skills/adapters/channels cannot elevate autonomy;
4. green routing cannot emit arbitrary commands;
5. routing never starts Harness;
6. routing never applies a patch;
7. routing never pushes, opens PRs or merges `main`;
8. routing never performs an external side effect.

## Non-goals

PR134 does not implement:

- natural-language execution;
- automatic Work;
- automatic Apply;
- free-form shell;
- source editing;
- Git commit/push/PR/merge;
- browser automation;
- n8n execution;
- MCP expansion;
- adapter dispatch;
- credentials;
- external messaging/publication;
- long-term memory.

## Acceptance

PR134 is complete when:

- `governed-conversational-routing/v1` is versioned;
- the canonical product index references it;
- the implementation matrix records it as contract-only;
- the operating plan identifies it after PR133;
- no runtime or authority is added.

A later implementation PR must begin from this contract and remain read-only
until a separate change explicitly connects a route to an existing governed
executor.
