# 04 — Review panel

Status: spec only. No implementation.

## Goal

Make review feel like a small pull request: files, validation, diff, and a clear decision. Do not expose promotion mechanics as manual hash work.

## When it appears

The review panel opens or highlights only when:

- a work run succeeds with a proposal;
- a review endpoint returns files/diff/patch metadata;
- a previous eligible proposal is selected from recent runs.

It remains hidden for fresh loads, read-only results, or work runs without changes.

## Content order

1. Review title and status.
2. Validation summary.
3. Changed files list.
4. Diff by file.
5. Telemetry summary.
6. Apply/Discard actions.
7. Debug link for raw metadata.

## Validation display

Use plain states:

- Passed;
- Failed;
- Missing;
- Stale;
- Truncated;
- Unknown.

If validation is missing, stale, failed, or truncated in a way that prevents complete review, Apply stays disabled.

## Diff rules

- Show relative paths only.
- Escape all diff content.
- Collapse long files by default.
- Show truncation clearly.
- Never infer hidden diff content as reviewed.
- If a diff cannot be displayed safely, block Apply and point to Debug.

## Apply rules

Apply button must be bound to the current workspace, current run id, current patch sha, and current review payload version if available. The user never copies hash in normal mode.

## Discard rules

Discard is visual abandonment unless a backend discard API exists. It should not imply sandbox deletion, rollback, or cleanup. It clears selected review state from the browser.

## Acceptance

- A successful work run can move from summary to review without manual run id or hash copy.
- Apply is disabled when validation is failed, missing, stale, truncated, or unknown.
- Switching workspace/run clears review and disables Apply.
- Promotion failure or unknown result does not display success.
