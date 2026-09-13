# 17 — Visual QA checklist

This checklist validates that the Workbench feels clean and usable without relying on internal implementation details.

## First load

Expected first impression:

- the page shows a clear Workbench title;
- project, mode, and status are visible;
- the main input is the obvious next action;
- Debug is collapsed;
- raw JSON is not the main interface;
- no field asks the user to manually paste run IDs or hashes in normal use.

## Mode cards

Expected behavior:

- Observe describes read-only work;
- Work describes sandboxed edits;
- Apply describes reviewed promotion;
- selecting a card does not execute anything;
- the primary action remains contextual and singular.
## Active run

During execution:

- Send is disabled or relabeled to prevent duplicate work;
- Cancel is available only for an active run;
- status does not depend on color alone;
- reconnect does not resend the same work;
- mode/context switching does not silently reuse old review state.

## Review state

When a Work run succeeds:

- review becomes the obvious next step;
- the UI shows file count and validation state before Apply;
- missing diff, truncation, drift, or missing hash blocks Apply;
- Debug remains available but secondary.

## Mobile/narrow viewport

On small screens:

- the chat remains primary;
- secondary navigation collapses;
- review is reachable without losing context;
- no new write-capable route becomes available.
