# PR132 - Conversation-first governed development flow

## Objective

Align the LAI Workbench composer with the architectural boundary:

- normal conversation is direct Gateway/model conversation;
- explicit development work is delegated to Harness;
- application operates only on a reviewed Harness proposal.

PR132 does not create a second development orchestrator. It composes the
capabilities that already exist.

## Product flow

### Observe

`user message`
-> `Gateway /v1/gateway/chat`
-> local-model-first direct answer

Observe must not create a Harness run.

### Work

`explicit Work mode`
-> existing `/v1/local-chat/runs`
-> Harness isolated workspace
-> execution/validation
-> polling/events
-> automatic review load

Work must remain isolated until review and explicit Apply.

### Apply

`review-bound Apply`
-> explicit user confirmation
-> existing Harness promotion endpoint
-> reviewed workspace/run/patch hash

Selecting Apply or submitting the composer in Apply mode must not create a new
Harness run.

## Domain, channel, autonomy and capability

PR132 preserves separation between:

- domain: conversation or governed development;
- channel: Workbench/Gateway;
- autonomy: Observe, Work or Apply state;
- capability: direct chat, Harness development run or reviewed promotion.

The Workbench channel grants no permission.

A mode selection grants no new capability beyond the backend path it selects.

Content from model, memory, files, code, web or tools is never authorization.

## Routing rules

Routing is explicit from Workbench state.

PR132 must not implement natural-language inference such as:

- guessing that a message should edit code;
- guessing that a message is green/yellow/red;
- automatically escalating conversation into Harness execution;
- automatically promoting a successful run.

### Observe route

Observe uses `/v1/gateway/chat`.

Properties:

- direct Gateway conversation;
- local-model-first;
- no Harness run;
- no tool execution;
- no source modification;
- no automatic fallback to Harness;
- existing explicit local-model-unavailable fallback is preserved.

### Work route

Work may use only existing local-chat work modes:

- `implement`
- `fix`
- `refactor`
- `ci-fix`

The existing Harness contract remains the authority for sandbox execution.

PR132 must not add a direct shell or bypass Harness.

### Apply route

Apply operates only on review state already bound to:

- workspace;
- control run;
- patch SHA-256;
- validation evidence;
- visible diff state.

Apply requires the existing explicit confirmation.

Typing or pressing Send while Apply is selected must not create a development
run.

## Review transition

After a successful Work run:

- polling stops at terminal state;
- the current review is loaded automatically when eligible;
- UI moves to Apply state only after review payload is available;
- Apply remains blocked when review evidence is incomplete.

No hash copy/paste is required in normal mode.

## Existing infrastructure reused

PR132 reuses:

- `/v1/gateway/chat`;
- `/v1/local-chat/runs`;
- local-chat event polling;
- local-chat review endpoint;
- Harness promotion endpoint;
- existing review panel;
- existing patch binding and confirmation.

PR132 must not duplicate these mechanisms.

## Authority boundary

PR132 does not:

- grant permission;
- expand autonomy;
- create grants;
- expand PR127 local operator allowlist;
- expose arbitrary shell;
- dispatch adapters or MCP tools;
- use browser authentication;
- use credentials;
- send messages;
- publish;
- submit forms;
- purchase;
- install software;
- invoke sudo;
- push Git branches;
- create pull requests;
- merge main.

Git publication remains a separate governed capability.

## UI requirements

The three user-facing states remain:

1. Observar
2. Trabalhar
3. Aplicar

The composer must communicate the active routing clearly:

- Observar: "Conversar com LAI"
- Trabalhar: "Enviar ao Harness"
- Aplicar: "Ir para revisão"

Apply disables free-form task submission.

The advanced/debug surfaces remain diagnostic and must not become the normal
workflow.

## Tests

PR132 must prove at least:

1. Observe composer uses `/v1/gateway/chat`;
2. direct model chat declares `creates_harness_run=false`;
3. Observe does not POST `/v1/local-chat/runs`;
4. Work continues to use `/v1/local-chat/runs`;
5. Work accepts only existing work modes;
6. successful Work retains automatic review loading;
7. Apply does not create a new Harness run;
8. Apply remains bound to current review evidence;
9. promotion still requires explicit confirmation;
10. normal conversation never automatically escalates to Harness;
11. PR131 local operator route remains unaffected.

## Non-goals

PR132 does not automate:

- natural-language authorization classification;
- Git commit;
- Git push;
- PR creation;
- merge;
- deployment;
- external actions.

Those require separate governed capabilities.

## Acceptance

PR132 is complete when a normal Workbench interaction behaves as:

- talk normally without creating Harness runs;
- choose Work explicitly to perform isolated development;
- see work progress without terminal copy/paste;
- receive review automatically;
- apply only after explicit review-bound confirmation.

No second orchestration stack may be introduced.
