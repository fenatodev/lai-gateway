# System transition checkpoint — 2026-09-13

Status: handoff checkpoint for OS/disk work after the LAI Gateway UI spec phase.

## Purpose

This document records the stable LAI project state before hardware, BIOS, bootloader, or OS installation work. It is a restart point, not an instruction to repartition disks or modify firmware.

## Stable repository state

| Repository | Branch | State | Last known commit |
| --- | --- | --- | --- |
| LAI Gateway | `main` | clean, synced with origin | `7c37c3a` |
| LAI Harness | `main` | clean, synced with origin | `eb5d495` |

## Installed versions

| Component | Version |
| --- | --- |
| `lai-gateway` | `0.1.34` |
| `lai harness` | `0.5.0` |

## Completed Gateway UI milestones

- `#50` exposed workbench phase telemetry in the UI.
- `#51` started the minimal Workbench shell and moved technical controls into collapsed Debug.
- `#52` guarded execution controls against duplicate sends and stale context reuse.
- `#53` added the full UI spec pack for the remaining Workbench design.
## Current capability boundary

The checkpoint preserves the existing security model:

- Harness owns local execution authority.
- Gateway serves UI/API orchestration only.
- Work runs remain local-first and loopback-scoped.
- Write-capable paths require sandbox, review, validation, and promotion gates.
- Browser-facing surfaces must avoid secrets, private absolute paths, unnecessary raw payloads, and direct machine authority.

## Not completed before transition

The following items are designed but not implemented:

- Review Panel MVP.
- Guided onboarding for non-technical users.
- Visual sidebar history polish.
- Automatic review fetch after successful Work run.
- Richer diff rendering.

These are safe to resume after system transition because the specs are now committed.
## Resume criteria after OS work

A resumed environment is acceptable when all of the following are true:

- Gateway and Harness repositories are restored on `main` and are clean.
- Gateway reports version `0.1.34` or newer.
- Harness reports version `0.5.0` or newer.
- The local model endpoint is reachable through the configured launcher.
- Gateway UI serves the minimal Workbench shell.
- A read-only run can be created and observed.
- A sandboxed Work run can finish without leaving the repository dirty.
- Review/promotion remains explicit and hash-bound.

## Stop conditions

Do not continue LAI feature work after system transition if:

- repository state is dirty for unknown reasons;
- model keys or Gateway tokens are missing or copied into public files;
- Gateway serves private/mobile mode with work routes enabled;
- the model starts with unexpected CPU-only or reduced-context defaults;
- a run cannot be cancelled or inspected after reconnect.
