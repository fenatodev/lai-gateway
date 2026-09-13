# 16 — Transition handoff

This spec defines the handoff point before system, disk, or firmware work.

## Goal

Make LAI resumable after interruption without relying on chat memory, terminal scrollback, or unstaged local edits.

## Handoff package

The repository must contain:

- the main Workbench architecture spec;
- the detailed UI spec pack;
- a system transition checkpoint;
- a post-restore runbook;
- changelog entries for the committed documentation.

## Required repository state

Before stopping for system work:

- Gateway is clean and synced with origin;
- Harness is clean and synced with origin;
- no open PR blocks the transition;
- no uncommitted UI spec remains only on disk;
- no generated runtime state is required to resume planning.
## Resume rule

After transition, do not continue implementation from memory. Resume by reading:

1. `docs/system-transition/CHECKPOINT-2026-09-13.md`
2. `docs/system-transition/POST-RESTORE-RUNBOOK.md`
3. `docs/ui/specs/15-incremental-roadmap.md`
4. the specific next feature spec

## Ideal next implementation after restore

The preferred next PR remains Review Panel MVP:

- clean review card;
- changed files;
- validation status;
- safe telemetry summary;
- diff display;
- explicit Apply confirmation.

Do not implement a full editor or default terminal before this path is complete.
