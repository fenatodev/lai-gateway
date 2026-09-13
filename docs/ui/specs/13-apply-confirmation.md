# 13 — Apply confirmation

Status: spec only. No implementation.

## Goal

Turn promotion into a clear reviewed decision without asking the user to manually manage patch hashes.

## Required evidence

Apply can be offered only when the UI has a current review payload containing:

- workspace identity;
- run identity;
- patch hash;
- changed files count;
- validation status;
- diff availability state.

## Confirmation copy

The confirmation should summarize:

```text
Apply this reviewed change?
Project: <display name>
Files changed: <count>
Validation: <status>
Patch: <short sha prefix>

This applies the reviewed patch through Harness promotion gates.
```

## Blocked states

Do not show Apply as enabled when:

- validation did not pass;
- review is stale;
- diff is hidden or materially truncated;
- workspace changed;
- run changed;
- patch hash is absent;
- access mode is not eligible.

## Result states

| Result | UI behavior |
| --- | --- |
| applied | show backend-confirmed success and clear active review |
| rejected | show reason and keep review visible |
| drift | require fresh review |
| unknown | ask user to check status before retrying |

## Acceptance

- User never manually copies patch hash in normal mode.
- Apply always uses the review-bound hash internally.
- A repeated click cannot submit multiple promotions for the same pending action.
