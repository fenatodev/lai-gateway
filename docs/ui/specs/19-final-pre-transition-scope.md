# 19 — Final pre-transition scope

This spec freezes the intended pre-transition scope so the project does not expand while system work is pending.

## Done before transition

The following are considered complete enough before hardware/OS work:

- minimal Workbench shell;
- execution control guards;
- full UI spec pack;
- system transition checkpoint;
- post-restore runbook;
- validation matrix;
- visual QA checklist.

## Explicitly deferred

The following are deferred until after the system is stable again:

- Review Panel MVP implementation;
- auto-open review after successful Work run;
- guided non-technical usage mode;
- richer sidebar history;
- full visual redesign;
- any native desktop packaging.
## Reasoning

Stopping here is safer than starting another UI implementation PR because the next work touches review, promotion, and user confirmation. That should be done only after the machine is stable and the restore checklist has passed.

## Required final state

Before transition, the repository should be left with:

- one docs-only PR merged;
- CI green;
- local repository clean;
- no open PRs;
- no running feature branch required for recovery.

## Next command after restore

Read the transition checkpoint first, then use the incremental roadmap to choose the next PR. Do not resume from memory alone.
