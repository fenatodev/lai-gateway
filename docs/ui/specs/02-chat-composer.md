# 02 — Chat composer

Status: spec only. No implementation.

## Goal

Operate LAI from one message box, with mode selection providing intent boundaries rather than exposing every internal run mode.

## Composer anatomy

Primary composer elements:

- selected project label;
- three-mode selector;
- textarea for the task;
- primary button;
- optional task length counter;
- compact hint for sandbox/review behavior.

## Mode behavior

Observe maps to safe read-only tasks. Work maps to sandboxed file-changing tasks. Apply does not start a new execution run; it moves the user to review/promotion for an existing eligible proposal.

| Visible mode | Default internal mode | Optional submodes |
| --- | --- | --- |
| Observe | `diagnose` | `plan`, `review`, `security`, `release` |
| Work | `implement` | `fix`, `refactor`, `ci-fix` |
| Apply | none | review/promotion for current proposal |

## Primary button labels

| State | Button |
| --- | --- |
| idle | Send to LAI |
| running | Run active |
| active cancellable | Cancel active run as secondary action |
| succeeded with proposal | Review change |
| reviewed and eligible | Apply change |
| failed | Inspect error |
| disconnected | Reconnect |

## Input rules

- Duplicate submit while active is blocked client-side and remains safe server-side.
- Empty messages are rejected before network calls.
- Mode changes during active execution are blocked.
- Changing project, workspace, or run invalidates any current review/hash.
- Multiline input remains easy; submit shortcut must be explicit.

## Response pattern

The chat response summarizes what LAI did, whether validation passed, whether files changed, and what the next action is. It does not dump raw events, stdout, stderr, or payloads by default.

## Acceptance

- User can start Observe/Work without touching workspace/model/run-id fields.
- The UI prevents duplicate sends while a non-terminal run is active.
- Apply cannot be selected as a new execution task without a proposal.
