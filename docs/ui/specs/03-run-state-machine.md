# 03 — Run state machine

Status: spec only. No implementation.

## Goal

Represent run state in the UI without conflating backend state, polling state, and user intention.

## Core state model

```text
idle
  -> preparing
  -> running
  -> validating
  -> terminal:succeeded
  -> terminal:failed
  -> terminal:timeout
  -> terminal:cancelled
```

Auxiliary frontend-only states:

- reconnecting;
- polling-stopped;
- cancelling;
- stale-review;
- unknown-after-network-error.

## Inputs

State may be driven by:

- run creation response;
- run/event polling response;
- lifecycle cancel response;
- review response;
- promotion response;
- network/polling errors.

## Invariants

- Stopping polling is not cancellation.
- Network failure is not run failure.
- Timeout must come from backend evidence, not elapsed browser time alone.
- Validation failure is terminal failed unless backend says otherwise.
- Promotion result may be unknown after network interruption; never assume success.

## Actions by state

| State | Primary action | Secondary action |
| --- | --- | --- |
| idle | Send to LAI | none |
| preparing/running/validating | disabled / Run active | Cancel |
| succeeded no change | New task | View summary |
| succeeded with proposal | Review change | New task |
| failed | Inspect error | Retry as new run |
| timeout | Inspect timeout | Retry with smaller task |
| cancelled | New task | View events |
| reconnecting | Reconnect | Stop polling |

## Data retention

Keep these in frontend state:

- selected workspace id;
- selected model id;
- active run id;
- active mode;
- last terminal status;
- review patch sha only for the currently selected run/workspace.

Clear patch/review state when workspace, run id, mode group, or project changes.

## Acceptance

- Duplicate submit is impossible from UI while active run is non-terminal.
- A polling error leaves the run recoverable by id.
- Cancel changes the UI to cancelling, then terminal cancelled only after backend evidence.
- A stale review cannot enable Apply.
