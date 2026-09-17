# PR128 — Local task content binding contract

PR128 specifies `local-task-content-binding/v1`.

This PR is documentation only.

## Objective

Close the content-identity gap between local task review, approval
classification and bounded execution before expanding the local executor.

## Scope

Specified:

- canonical content digest for `local-task/v1`;
- explicit digest algorithm/version;
- propagation from review to approval;
- recomputation at execution time;
- fail-closed mismatch behavior;
- separation between content identity and authorization;
- follow-up implementation boundaries.

Not implemented:

- digest runtime code;
- changes to review, approval or executor modules;
- new executable commands;
- broader shell access;
- grants or permission changes;
- Harness, adapter or tool execution;
- credentials or external effects.

## Acceptance

PR128 is acceptable only if the documentation makes these properties explicit:

- `task_id` is correlation, not content identity;
- digest input is the parsed `local-task/v1` object;
- duplicate JSON object keys are rejected before hashing;
- canonical bytes use the explicitly defined Python JSON serialization;
- formatting or object key order alone does not change the digest;
- a change to the canonical bytes changes the digest;
- Unicode is not normalized in v1;
- numeric forms such as `1` and `1.0` remain distinct in v1;
- review output carries the task digest;
- approval output preserves the same digest;
- executor must recompute and compare before executing;
- digest validity never grants authorization;
- the digest is not a signature, MAC, provenance proof or tamper-evident log;
- executor allowlist expansion is outside this PR;
- `local-task-outbox/v1` binding is deferred until it becomes operational input.
