# 01 — Information architecture

Status: spec only. No implementation.

## Goal

Make the Workbench feel like a small agent console: project context, chat, status, and review. Hide operational plumbing until it is needed.

## Primary surface

The first screen should answer four questions without scrolling:

- Which project is selected?
- Which mode is selected?
- What should LAI do?
- What is the current run state?

Primary controls:

- mode selector: Observe, Work, Apply;
- message composer;
- one primary contextual action;
- run status summary;
- next recommended action.

## Secondary surface

Show secondary information only when relevant:

- review panel after a work run has a proposal;
- error panel after failure, timeout, or validation failure;
- reconnect affordance after lost polling;
- concise run telemetry after terminal status.

## Debug surface

Debug stays collapsed by default:

- sanitized raw payloads;
- run id;
- patch sha;
- full event list;
- model selection;
- local-chat contract;
- diagnostic controls.

## Layout

```text
+--------------------------------------------------+
| Header: project, branch, readiness, model status |
+-------------+-----------------------+------------+
| Sidebar     | Chat / Composer       | Review     |
| projects    | Mode selector         | contextual |
| sessions    | Run state             | hidden     |
| recent runs | Primary action        | by default |
+-------------+-----------------------+------------+
| Advanced / Debug collapsed                      |
+--------------------------------------------------+
```

## Rules

- Do not show empty panels as if they require action.
- Do not require the user to copy or paste IDs/hashes in normal mode.
- Do not show raw payloads unless Debug is open.
- Do not add backend authority just to simplify the UI.
- Do not hide security-critical decisions; simplify their presentation.

## Acceptance

- A fresh page load shows no `run id`, `patch sha`, raw payload, terminal, or model selector on the primary surface.
- A work result reveals review context without exposing Debug by default.
- Switching projects or runs clears stale review state.
