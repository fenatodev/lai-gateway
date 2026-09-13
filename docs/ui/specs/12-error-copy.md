# 12 — Error copy

Status: spec only. No implementation.

## Goal

Errors should tell the user what happened, what is known, and what can be done next. They should not expose raw internals by default.

## Error classes

| Class | User copy pattern |
| --- | --- |
| capability missing | This project does not expose the required workbench capability. |
| validation failed | LAI produced a change, but validation failed. Review the failure before retrying. |
| timeout | The backend reported a timeout. The run may have partial workspace changes, but nothing was applied. |
| network lost | The browser lost contact with the Gateway. Reconnect before deciding. |
| promotion blocked | Apply is blocked because review evidence is incomplete or stale. |
| promotion unknown | The Apply request did not return a final result. Check status before retrying. |

## Copy rules

- Start with the user-facing effect.
- Include only safe cause details.
- Offer one next action.
- Put detailed payloads in Debug.
- Never say “applied” without backend confirmation.

## Acceptance

- Every blocked action explains why.
- Failed validation and network failure are visibly different.
- Errors never train the user to bypass review or use manual hash entry.
