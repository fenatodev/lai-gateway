# 15 — Incremental roadmap

Status: spec only. No implementation.

## Goal

Prevent the UI redesign from becoming a large unreviewable rewrite.

## PR sequence

### PR A — Review panel MVP

Scope:

- dedicated review area;
- files changed;
- validation summary;
- diff output;
- Apply/Discard visual actions.

No new backend routes.

### PR B — Sidebar and recent runs

Scope:

- project/workspace list;
- recent runs list;
- needs-review marker;
- selection invalidates stale review state.

No file explorer or editor.

### PR C — Polished state machine

Scope:

- explicit reconnect state;
- cancelling state;
- blocked-reason display;
- keyboard/focus refinements;
- improved empty states.

No authority changes.

## Cut line

Each PR must be mergeable alone, pass current checks, preserve private/mobile restrictions, and avoid changing Harness behavior.

## Acceptance

- No PR mixes visual redesign, backend authority, and run lifecycle semantics at once.
- Each PR has static UI assertions and at least one relevant fake Harness fixture when behavior changes.
