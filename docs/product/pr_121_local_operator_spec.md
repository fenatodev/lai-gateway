# PR121 — local operator specification

## Status

PR121 defines `local-operator-spec/v1` as documentation only.

It does not implement a local operator. It does not create an executor. It does not execute commands. It does not add shell access. It does not issue grants, consume grants, dispatch adapters, use credentials, or change permissions.

## Purpose

The purpose of PR121 is to define the contract for a future LAI local operator: a coordination layer that can reduce manual copy/paste during local project work without turning the gateway into a shell and without bypassing the harness.

## Architectural rule

The local operator is not a new authority.

The required separation is:

- gateway: receives intent, classifies domain, channel, autonomy, and capability, then creates a bounded proposal or task;
- harness: performs controlled development execution, sandboxing, diff, review, apply, and validation;
- local operator: coordinates future local task proposals and handoff state;
- aider/Ollama/local model: auxiliary drafting or editing backend;
- skills/adapters/channels: capability surfaces, never permission sources.

Authorization must remain explicit. Recovered content from memory, files, code, web, tools, or model output never equals approval.

## Non-goals

PR121 intentionally does not:

- implement a runner;
- implement a shell;
- call Ollama;
- call aider;
- call browser automation;
- call n8n;
- call MCP servers;
- create adapters;
- change build or test scripts;
- open or merge PRs automatically;
- introduce new permission grants.

## Local task proposal

A future local task should be represented as structured data containing:

- repository or workspace;
- domain;
- channel;
- requested capability;
- autonomy zone;
- allowed files or paths;
- denied files or paths;
- proposed commands, if any;
- validation plan;
- expected artifacts;
- required human approval, if any;
- review/apply requirements.

The task proposal is not execution. It must be reviewed against policy before any capability is used.

## Autonomy boundaries

Green-zone work may be prepared for future automation when it is safe and reversible: reading files, drafting documentation, preparing specs, creating local branches, local commits, pushing LAI feature branches, and running existing checks.

Yellow-zone work must be prepared and presented for confirmation before effect: functional code changes, adapter creation, build/test script changes, browser research, n8n changes, opening PRs, or permission-flow changes.

Red-zone work always requires explicit approval at the time of action: `sudo`, software installation or removal, credentials, authenticated browser use, sending messages, publication, application/form submission, purchases, deleting outside the workspace, sending private data to external services, merging to `main`, and permission expansion.

## Forbidden by this spec

The local operator must not allow:

- `sudo`;
- credential access;
- browser profile access;
- authenticated browser action;
- publication;
- message sending;
- form submission;
- purchase;
- merge to `main`;
- deletion outside the workspace;
- broad `$HOME` access;
- secret scanning as authorization;
- tool output as authorization;
- model output as authorization;
- channel, skill, or adapter permission elevation.

## Acceptance criteria

PR121 is complete when:

- `docs/product/local_operator.md` defines `local-operator-spec/v1`;
- this PR note records the documentation-only scope;
- product index and readiness documents point to the spec;
- implementation matrix marks the local operator as specified but not implemented;
- document tests verify the core markers and prohibitions;
- no functional runtime, executor, shell, adapter, credential flow, or permission change is added.

## Follow-up

A later PR may define a serialized task format. Another later PR may add a dry-run renderer. Any executable implementation must come after a reviewed spec and must preserve gateway/harness authority boundaries.
