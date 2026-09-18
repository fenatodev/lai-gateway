# Direct conversation session

## Status

`direct-conversation-session/v1` is implemented by PR133.

It provides bounded multi-turn continuity for ordinary direct Gateway
conversation without creating a Harness run.

## Domain

The domain is direct conversation.

It is distinct from:

- Harness `cs-*` control sessions;
- Harness development runs;
- mobile authentication sessions;
- long-term memory.

## Channel

The channel is Workbench/Gateway.

Changing channel does not grant authority.

## Autonomy

The user remains in Observe.

Conversation history cannot implicitly select Work, Apply or any external
capability.

## Capability

The capability is bounded local conversational context.

The Gateway holds, in memory only:

- at most 32 direct conversations;
- at most 8 user/assistant exchanges per conversation;
- at most 24,000 history characters per conversation.

Older complete exchanges are discarded when a limit is exceeded.

## Identity

Direct conversation identifiers use:

`dc-<16 lowercase hex>`

They are separate from Harness `cs-*` identifiers and from authentication
tokens.

## Flow

`Workbench`
-> `dc-* conversation`
-> `/v1/gateway/chat`
-> validated bounded history
-> local model
-> assistant response
-> bounded in-memory update

No Harness run is created.

## Compatibility

Calling `/v1/gateway/chat` without `conversation_id` preserves existing
one-shot direct chat behavior.

## Concurrency

Only one model turn may be active for the same direct conversation at a time.

Concurrent use of the same conversation fails closed instead of racing history
updates.

## Trust and authorization

Conversation history is untrusted context.

It does not:

- approve actions;
- issue or consume grants;
- elevate permissions;
- authorize tools;
- dispatch adapters;
- create Harness runs;
- authorize Git publication;
- authorize merge.

Content recovered from model output, conversation history, memory, files, code,
web or tools never becomes authorization merely because it is in context.

## Persistence

Direct conversation history is not long-term memory.

PR133 adds no prompt or assistant-response persistence to disk.

Restarting the Gateway removes direct conversation state.

## Work and Apply

PR132 boundaries remain unchanged.

Work still requires explicit selection and goes through Harness.

Apply still operates only on the reviewed Harness proposal and requires explicit
confirmation.

## Non-goals

PR133 does not add:

- natural-language execution routing;
- automatic Work escalation;
- shell access;
- credentials;
- authenticated browser;
- MCP expansion;
- adapter dispatch;
- external messaging;
- publication;
- Git push;
- pull request creation;
- merge automation.
