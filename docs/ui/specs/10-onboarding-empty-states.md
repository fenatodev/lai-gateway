# 10 — Onboarding and empty states

Status: spec only. No implementation.

## Goal

Make a first-time user understand what LAI can do without reading technical docs or opening Debug.

## First load

The first load should show:

- selected project or clear “project not loaded” state;
- current system readiness summary;
- three available modes;
- one example prompt for Observe;
- one example prompt for Work if work capability is available.

## Empty states

| Context | Empty copy |
| --- | --- |
| no workspace | Load or register a project before running LAI. |
| no session | Start a task; session will be created or reused when supported. |
| no run | Ask LAI what to inspect or change. |
| no review | No proposed change is ready for review. |
| no model | Model is not available; check model status in Debug. |

## Guardrails

Empty states must not imply capabilities that are absent. If local-chat work is unavailable, Work should explain why instead of silently disappearing.

## Acceptance

- Fresh UI gives a safe first action.
- Missing capability appears as a clear reason, not as broken UI.
- No empty state requires manual run id or hash entry.
