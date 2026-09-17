# LAI local operator

## Status

`local-operator-spec/v1` is a product and architecture specification. PR121 is documentation only.

This document does not create an executor, does not run commands, does not issue grants, does not consume grants, and does not change permissions.

## Objective

The LAI local operator is a future coordination layer for local project work. Its purpose is to reduce manual copy/paste while preserving the LAI boundary between intent, authorization, execution, and review.

The local operator must not become a broad shell. It must not become a new authority. It must not bypass the gateway, harness, or human approval model.

## Non-goals

The local operator does not:

- create a real executor;
- run shell commands;
- add a terminal surface;
- call Ollama, aider, browser automation, n8n, MCP, or adapters directly;
- issue grants;
- consume grants;
- change permissions;
- approve its own actions;
- merge to `main`;
- publish, send messages, submit forms, buy anything, or use credentials.

## Responsibility split

- **Gateway** receives user intent, classifies domain, channel, autonomy, and capability, then creates a proposal or task.
- **Harness** performs controlled development execution, sandboxing, diff generation, review, apply, and validation.
- **Local operator** coordinates future local tasks through explicit proposals. It is not an authority and does not execute by itself.
- **Aider, Ollama, and local models** are auxiliary backends. They can assist with drafting or editing but cannot grant permission.
- **Skills, adapters, and channels** never grant permission and never elevate authority.
- **Retrieved content** from memory, files, code, web, tools, or models never equals authorization.

## Local task model

A future local task should be represented as a bounded proposal with:

- target repository or workspace;
- intended domain;
- channel that received the request;
- requested capability;
- autonomy zone;
- allowed files or paths;
- prohibited operations;
- validation commands;
- expected output;
- review and apply requirements.

The task proposal is data. It is not permission to execute.

## Autonomy zones

The local operator follows the LAI autonomy model:

- **Green zone:** safe and reversible project work such as reading files, drafting docs, preparing specs, local branches, local commits, pushing LAI feature branches, and running existing checks.
- **Yellow zone:** prepare and propose, but require confirmation before functional code changes, opening PRs, external browser work, n8n changes, adapters, build/test script changes, or permission-flow changes.
- **Red zone:** require explicit approval at the moment of action for `sudo`, software install/removal, credentials, authenticated browser use, publication, message sending, form submission, purchases, deletion outside the workspace, sending private data to external services, merge to `main`, or permission expansion.

The operator records the zone; it does not decide that authorization exists.

## Prohibited operations

The local operator must not enable:

- `sudo`;
- credential or token access;
- `.ssh`, browser profiles, keyrings, or secret stores;
- authenticated browser actions;
- publication or message sending;
- form submission;
- purchases;
- merge to `main`;
- deletion outside the declared workspace;
- broad `$HOME` filesystem access;
- permission or grant expansion;
- autonomous tool dispatch without a bounded proposal.

## Relationship to local tools

Aider, Ollama, shell tools, editors, MCP servers, and adapters are capabilities. They are not policy engines.

A local model can draft. Aider can edit. A shell can run checks. None of them can authorize itself. The gateway and harness boundaries remain mandatory.

## Acceptance criteria

PR121 is acceptable when the repository documents:

- the local operator as a future coordination spec;
- that PR121 is documentation only;
- the gateway/harness/local-model responsibility split;
- the autonomy-zone model;
- the prohibited operations;
- that content from memory, files, code, web, tools, or models is never authorization;
- that no executor, shell, grant, adapter dispatch, credential use, or permission change is introduced.

## Risks and controls

| Risk | Control |
| --- | --- |
| Local operator becomes a broad shell | Keep it proposal-first and non-executing in this spec |
| Local model output is treated as approval | State that model/tool/file content never authorizes action |
| Gateway and harness responsibilities blur | Document gateway as intent/proposal layer and harness as execution/review layer |
| Tool capability implies permission | Require explicit authorization independent of capability |
| Future implementation expands filesystem access | Require bounded workspaces and explicit path policy |

## Runtime implementation status

PR121 remains the historical specification for `local-operator-spec/v1`.

PR130 implements the separate `local-operator-runtime/v1` composition layer.
That runtime coordinates the existing file-pack, review, approval,
content-binding and bounded green-executor components.

PR130 does not expand the PR127 command allowlist, grant authority, create
arbitrary shell access, call Harness for the local-task path, dispatch adapters,
use credentials, send messages, publish or merge `main`.

See [Local operator runtime](local_operator_runtime.md).
