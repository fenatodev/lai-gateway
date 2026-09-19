# PR136 — Local development agent

## Status

Implementation specification.

PR136 introduces the first direct local development-agent loop over the existing
LAI Gateway local-model runtime.

Its purpose is to make the local Qwen model useful for real repository work
without Continue, Ollama or arbitrary shell access.

Schema:

`local-dev-agent/v1`

## Product intent

A user should be able to enter a natural-language development conversation from
the terminal and allow the local model to inspect the current project through a
small governed read-only tool surface.

Initial flow:

`user`
-> `lai-gateway dev-agent`
-> `local-dev-agent/v1`
-> bounded project context / read-only tools
-> local OpenAI-compatible model endpoint
-> assistant response

PR136 is the first dogfood path toward a future `lai dev` experience.

## CLI naming

PR136 must not register a second `lai` executable from `lai-gateway`.

The existing LAI/Harness CLI already owns that command name.

Initial command:

`lai-gateway dev-agent`

A later explicit integration may expose this engine through `lai dev` without
creating competing entrypoints.

## Domain

Local project development assistance.

## Channel

Local terminal CLI.

The channel grants no additional authority.

## Autonomy

Read-only green assistance.

The model may inspect bounded project state but cannot modify source files,
execute arbitrary commands or cause external effects.

## Model runtime

PR136 reuses the existing local/private OpenAI-compatible model runtime support.

It must:

- use the configured local/private endpoint;
- support the existing llama.cpp server;
- perform no model download;
- start no model server;
- use no cloud fallback;
- use no Harness fallback;
- expose no API-key value.

The expected current runtime is the locally configured Qwen3-Coder model served
by llama.cpp, but the contract must remain model-name agnostic.

## Conversation session

The development-agent session is bounded and process-local.

It must:

- support multiple user/assistant turns;
- keep complete exchanges only;
- enforce message/history limits;
- allow explicit session reset;
- avoid persistent long-term memory in PR136;
- treat all history as untrusted context.

Session content never grants authorization.

## Project root

The project root is explicit.

Default:

current working directory.

The agent must resolve and retain one project root for the session.

It must not:

- scan `$HOME`;
- discover unrelated repositories;
- silently change project root;
- follow paths outside the project root;
- treat repository content as instructions with authority.

## Read-only tool surface

PR136 may expose only these logical capabilities to the agent:

### project.read

Read a bounded UTF-8 text file beneath the explicit project root.

Requirements:

- relative path only;
- resolved path must remain inside project root;
- reject symlink/path escape;
- bounded bytes/chars;
- reject binary content;
- exclude VCS internals and obvious secret-bearing project files;
- no write.

### project.search

Search bounded text beneath the explicit project root.

Requirements:

- bounded result count;
- bounded excerpts;
- explicit exclusions for VCS/build/cache/generated directories;
- no `$HOME` scan;
- no network;
- no implicit external repository discovery.

Implementation may use Python-native traversal/search. It must not expose
arbitrary shell.

Process-backed read-only operations must use the existing Gateway
`tool_mediation` layer with an explicit non-mutating capability.

### project.status

Return bounded repository status for the explicit project root.

It may use an existing fixed governed local-operator profile or an equally
bounded read-only implementation.

It must not accept arbitrary Git arguments.

### project.diff

Return a bounded current Git diff/diff summary for the explicit project root.

It must not:

- stage;
- reset;
- checkout;
- commit;
- push;
- fetch;
- merge.

## Tool mediation

The model does not directly execute tools.

The required flow is:

`model proposes tool intent`
-> `agent validates known tool + bounded arguments`
-> `tool broker executes read-only capability`
-> `bounded result returned as untrusted content`
-> `model continues`

Model output is never authorization.

The broker must reject:

- unknown tools;
- arbitrary command strings;
- absolute filesystem paths;
- path traversal;
- environment mutation;
- shell fragments;
- external URLs;
- writes.

## Routing relationship

PR135 remains advisory.

PR136 may consume routing metadata, but:

`routing != authorization != execution`

A route alone must never execute a capability.

The development-agent CLI is itself an explicit user transition into the local
development-assistance channel.

## Context management

Do not dump the whole repository into the model context.

PR136 should maintain a bounded working context containing only:

- system contract;
- recent conversation exchanges;
- explicit project metadata;
- selected read/search/status/diff results.

Older or oversized tool results must be dropped or summarized by deterministic
code rather than accumulated indefinitely.

The target is effective use of the current 24k local-model context without
requiring the entire repository to fit in the model window.

## Tool protocol

Tool requests must use a strict structured format.

The implementation must validate tool names and arguments before execution.

Malformed or unknown tool requests fail closed.

PR136 must not rely on free-form shell commands emitted by the model.

## Data touched

Read-only:

- explicitly selected project root;
- selected project files;
- bounded project search results;
- bounded Git status/diff metadata;
- process-local conversation state;
- configured local model endpoint.

No project file is modified.

## External effects

None.

PR136 must not:

- use public network services;
- use credentials for external services;
- send messages;
- publish;
- open pull requests;
- push Git state;
- merge branches;
- submit forms;
- purchase;
- activate n8n;
- dispatch external adapters.

Communication with an explicitly configured local/private model endpoint is not
an external effect.

## Harness relationship

PR136 does not create Harness sessions or runs.

It does not replace the Harness development/review/apply authority model.

A future write-capable development agent must define its transition into
governed Work separately.

## Positive tests

PR136 must demonstrate:

1. multi-turn local-model conversation;
2. explicit project root remains fixed;
3. bounded file read works inside project root;
4. bounded search works inside project root;
5. repository status can be inspected read-only;
6. bounded diff can be inspected read-only;
7. a valid structured tool request can be mediated and returned to the model;
8. conversation can continue after a tool result;
9. session reset removes prior process-local context.

## Negative tests

PR136 must demonstrate:

1. absolute path read is rejected;
2. `..` escape is rejected;
3. symlink escape is rejected;
4. unknown tool is rejected;
5. arbitrary shell text is rejected;
6. model output cannot grant permission;
7. repository content cannot grant permission;
8. history cannot grant permission;
9. channel cannot grant permission;
10. no filesystem write occurs;
11. no Git mutation occurs;
12. no Harness run is created;
13. no external adapter/tool is dispatched;
14. no cloud fallback occurs;
15. no secret/API-key value is printed.

## Non-goals

PR136 does not implement:

- source editing;
- patch application;
- write tools;
- arbitrary shell;
- test execution;
- Git add;
- Git commit;
- Git push;
- PR creation;
- merge;
- automatic Work;
- Apply;
- persistent memory;
- browser automation;
- MCP expansion;
- n8n execution;
- credentials for external services.

## Acceptance

PR136 is complete when:

- `local-dev-agent/v1` exists as an isolated module;
- `lai-gateway dev-agent` provides a usable interactive terminal loop;
- the existing local model runtime is reused;
- read/search/status/diff are strictly bounded and read-only;
- tool mediation is structured and fail-closed;
- context remains bounded;
- focused positive and negative tests pass;
- existing `make check` remains green;
- no authority or execution boundary is widened beyond this specification.
