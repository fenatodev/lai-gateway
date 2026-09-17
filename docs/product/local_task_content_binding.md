# Local task content binding

Status: specified, not implemented.

`local-task-content-binding/v1` defines content identity for `local-task/v1`
records as they move through review, approval classification and bounded local
execution.

The purpose is to prevent a task from being reviewed and then modified while
retaining the same `task_id`.

## Problem

`task_id` is a correlation identifier. It is not proof that two task records
contain the same content.

The current local task chain correlates review, approval and bounded execution
by `task_id`. Before the executor is expanded, content identity must also be
preserved across that chain.

## Contract

A task content digest is computed from the parsed `local-task/v1` JSON object.

The digest contract is `sha256-canonical-json-v1`.

Canonical serialization requirements:

- JSON encoded as UTF-8;
- object keys sorted recursively;
- insignificant whitespace removed;
- non-ASCII characters preserved;
- NaN and Infinity rejected;
- digest represented as `sha256:<lowercase hexadecimal digest>`.

Equivalent parsed JSON objects that differ only in key order or insignificant
formatting must produce the same digest.

Any change to the canonicalized task representation must produce a different
digest.

The implementation must use one shared canonicalization function rather than
duplicating serialization rules across gates or executors.

## Lifecycle

The required chain is:

1. load `local-task/v1`;
2. compute `task_digest`;
3. `local-task-review-gate/v1` carries `task_digest`;
4. `local-task-approval-gate/v1` requires and carries the same `task_digest`;
5. `local-task-green-executor/v1` recomputes the digest from the task it loads;
6. execution is allowed only when the recomputed digest matches the reviewed
   and approval-gate digest.

`task_id` remains required for correlation, but `task_id` alone is insufficient
for content identity.

The executor must derive both the digest and executable command set from the
same parsed task record.

## Required behavior

The content binding must fail closed when:

- the review output has no valid `task_digest`;
- the approval input changes or loses the reviewed `task_digest`;
- the task loaded by the executor produces a different digest;
- the digest algorithm or format is unknown;
- the task cannot be canonicalized deterministically.

A mismatch is invalid input. It must not become an automatic approval request.

## Security properties

The digest binds content. It does not grant authority.

A valid `task_digest` must not:

- create effective authorization;
- issue or consume a grant;
- change autonomy zone;
- remove a human approval requirement;
- expand an executor allowlist;
- permit arbitrary shell;
- authorize Harness, adapters or tools;
- authorize credentials, messages, publication or merge.

Content recovered from files, memory, models or tools remains untrusted data
and does not become authorization because it has a digest.

## Initial scope

PR128 specifies binding for `local-task/v1` only.

`local-task-outbox/v1` remains correlated by `task_id` because the current green
executor does not consume outbox content as execution authority or command
input.

If a future executor consumes outbox content operationally, that content must
receive its own binding contract before execution.

## Non-goals

PR128 does not implement hashing code, gate changes, executor changes, new
commands, new allowlist entries, grants, permission changes, Harness calls,
adapter dispatch, tool execution or external effects.

## Follow-up implementation

A later functional PR may implement this contract by:

1. adding one shared canonical task digest helper;
2. emitting `task_digest` from the review gate;
3. requiring and propagating it through the approval gate;
4. recomputing and checking it in the green executor;
5. adding positive and mutation-negative tests.

That implementation must not broaden the PR127 command allowlist as part of the
same change.
