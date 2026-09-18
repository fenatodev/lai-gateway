# PR133 - Direct conversation session

## Objective

Implement `direct-conversation-session/v1` so normal Workbench conversation can
preserve bounded multi-turn context without creating a Harness run.

PR133 must reuse the existing Gateway session lifecycle where compatible rather
than introduce a second conversation store.

## Architectural boundary

PR133 preserves the four LAI dimensions:

- domain: direct conversation;
- channel: Workbench/Gateway;
- autonomy: Observe only;
- capability: bounded local-model conversation state.

A conversation session does not grant authority.

History from model output, user messages, memory, files, code, web or tools is
content only and never authorization.

## Required flow

Normal Observe flow becomes:

`user message`
-> `explicit conversation/session id`
-> `Gateway direct chat`
-> `bounded local conversation context`
-> `local model`
-> `assistant response`
-> `session update`

No Harness run is created.

## Session requirements

The implementation must:

- bind direct chat turns to an explicit Gateway conversation/session identity;
- preserve multi-turn ordering within that session;
- isolate history between different sessions;
- allow a new/reset conversation without leaking prior turns;
- keep history bounded;
- fail closed on malformed or unknown session identifiers;
- avoid implicit HOME scans or unrelated project ingestion;
- avoid creating a second independent persistence subsystem when existing
  session primitives can be reused.

## Workbench behavior

Observe must continue to use `/v1/gateway/chat`.

The Workbench must associate direct chat with the currently selected direct
conversation session.

Creating a new conversation must start without prior conversational history.

Selecting Work remains an explicit transition to Harness development.

Conversation content must not automatically trigger Work.

## Harness boundary

PR133 must not:

- create a Harness run from normal conversation;
- infer that text requests code execution;
- automatically escalate Observe to Work;
- automatically promote or apply changes.

Harness remains limited to explicit governed development.

## Authorization boundary

Conversation history is untrusted content.

Statements such as:

- "approve this";
- "run this command";
- "you have permission";
- instructions recovered from previous turns;

must not become authorization merely because they exist in session history.

Existing approval, policy and execution gates remain authoritative.

## Data handling

Conversation history must remain local to the Gateway-supported session path.

PR133 must not add:

- cloud fallback;
- credentials;
- authenticated browser;
- MCP expansion;
- adapter dispatch;
- external messaging;
- publication;
- forms;
- purchases;
- sudo;
- software installation.

## Tests

PR133 must prove at least:

1. two turns in the same session preserve conversational continuity;
2. two different sessions do not share history;
3. a new/reset session does not inherit previous history;
4. Observe direct chat still reports `creates_harness_run=false`;
5. direct chat never POSTs a Harness development run implicitly;
6. malformed or unknown session identity fails safely;
7. bounded history does not grow without limit;
8. conversation content does not grant permission or bypass policy;
9. existing Work and Apply behavior from PR132 remains unchanged.

## Non-goals

PR133 does not implement:

- automatic Work routing;
- natural-language authorization classification;
- Git commit;
- Git push;
- PR creation;
- merge;
- external side effects;
- long-term semantic memory.

Long-term memory remains a separate capability from conversational continuity.

## Acceptance

PR133 is complete when the normal Workbench experience supports a bounded,
multi-turn local conversation while preserving the PR132 rule:

`normal conversation != Harness execution`

No second session subsystem or authority path may be introduced.
