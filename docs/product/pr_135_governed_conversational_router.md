# PR135 — Governed conversational router

## Status

Implementation spec.

PR135 implements the read-only classifier defined by
`governed-conversational-routing/v1`.

It classifies natural-language requests into advisory routing outcomes without
executing them.

## Domain

Conversational intent routing inside the LAI Gateway.

## Channel

Workbench/Gateway direct conversation.

Channel does not grant authority.

## Autonomy

Read-only classification only.

PR135 does not execute any classified action.

## Capability

The router may classify a request as:

- `conversation`
- `local_green_candidate`
- `work_candidate`
- `approval_required`
- `clarify`
- `blocked`

## Executor

None.

PR135 must not invoke:

- Harness;
- local operator runtime;
- shell;
- adapters;
- MCP tools;
- external services.

## Data touched

Input may include only bounded explicit request context, such as:

- current user message;
- current mode;
- bounded conversation context;
- metadata for known fixed local-operator profiles.

PR135 must not:

- scan `$HOME`;
- discover unrelated repositories;
- ingest arbitrary files implicitly;
- treat retrieved content as authorization.

## Routing result

The classifier returns a bounded structured record containing at least:

- `schema_version`
- `route`
- `domain`
- `channel`
- `autonomy`
- `capability`
- `reason_code`
- `requires_explicit_transition`
- `requires_approval`
- `creates_harness_run`
- `grants_authority`
- optional `local_operator_profile`

Required invariants:

- `creates_harness_run = false`
- `grants_authority = false`

## Routing rules

### conversation

Ordinary conversational requests remain in direct conversation.

No Harness run is created.

### local_green_candidate

May reference only an existing fixed green local-operator profile.

The router must not synthesize:

- shell commands;
- argv;
- repository roots;
- arbitrary tool calls.

Classification does not execute the profile.

### work_candidate

Represents development work that may require Harness.

The result is advisory only.

Explicit transition to Work remains required.

### approval_required

Used when the requested effect belongs to yellow or red autonomy.

Classification does not constitute approval.

### clarify

Used when intent is ambiguous or required information is missing.

### blocked

Used when the capability is unsupported or cannot be represented safely.

## Authorization policy

The invariant is:

`routing != authorization != execution`

Conversation history, model output, memory, files, code, web and tool content are
untrusted context and never authorization.

Skills, adapters and channels never elevate autonomy.

Approval-like text found in history must not alter authority.

## Positive tests

PR135 must demonstrate:

1. ordinary conversation -> `conversation`;
2. supported fixed green validation request -> `local_green_candidate`;
3. development request -> `work_candidate`;
4. yellow/red request -> `approval_required`;
5. ambiguous request -> `clarify`;
6. unsupported capability -> `blocked`.

## Negative tests

PR135 must demonstrate:

1. history cannot grant permission;
2. model output cannot elevate autonomy;
3. skills/adapters/channels cannot elevate autonomy;
4. arbitrary command text never becomes a green executable command;
5. router never starts Harness;
6. router never invokes local operator runtime;
7. router never applies patches;
8. router never emits grants;
9. router never performs external side effects;
10. router never pushes, opens PRs or merges `main`.

## Implementation constraints

Prefer an isolated routing module instead of embedding policy logic in
`server.py`.

The implementation must be deterministic where possible and fail closed.

PR135 may expose classification through a read-only module/API surface, but it
must not connect classification output to execution.

## Non-goals

PR135 does not implement:

- automatic Work;
- automatic Apply;
- shell execution;
- source editing;
- local operator execution;
- Git commit/push/PR/merge;
- adapter dispatch;
- MCP execution;
- browser automation;
- credentials;
- messaging;
- publication;
- long-term memory.

## Acceptance

PR135 is complete when:

- the classifier implements all six routes;
- routing output is bounded and structured;
- all authority fields remain non-authorizing;
- focused positive and negative tests pass;
- no execution path is connected;
- canonical documentation reflects the implementation state.
