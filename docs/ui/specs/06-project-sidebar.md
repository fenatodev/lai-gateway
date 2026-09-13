# 06 — Project sidebar

Status: spec only. No implementation.

## Goal

Give VS Code-style orientation without creating a full file explorer or editor.

## Sidebar sections

- Projects/workspaces;
- Sessions;
- Recent runs;
- Optional filters: all, active, needs review, failed.

## Project item

Each project item shows:

- display name;
- branch if available;
- clean/dirty indicator;
- capability availability.

Do not show absolute local paths by default.

## Run item

Each run item shows:

- human title or first safe summary line;
- mode group: Observe or Work;
- status;
- age/duration if available;
- needs-review marker if eligible.

## Selection rules

Selecting a project:

- changes workspace context;
- clears active review/hash;
- keeps unsent composer text only if it is clearly local draft text;
- reloads model choices internally.

Selecting a run:

- loads summary/events/review if supported;
- never replays the task;
- never promotes automatically.

## Responsive behavior

On narrow screens:

- sidebar becomes a drawer;
- current project remains visible in header;
- review becomes a tab or stacked section;
- primary action remains reachable without horizontal scrolling.

## Acceptance

- User can identify current project without opening Debug.
- User can resume a recent run without copying run id.
- Sidebar never becomes a file tree/editor replacement.
