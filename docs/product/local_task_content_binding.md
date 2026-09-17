# Local task content binding

Status: implemented by PR129.

`local-task-content-binding/v1` defines content identity for `local-task/v1`
records as they move through review, approval classification and bounded local
execution.

The purpose is to prevent a task from being reviewed and then modified while
retaining the same `task_id`.

## Problem

`task_id` is a correlation identifier. It is not proof that two task records
contain the same content.

Before PR129, the local task chain correlated review, approval and bounded
execution by `task_id` only. PR129 implements content identity across that
chain using `task_digest`.

## Contract

A task content digest is computed from the parsed `local-task/v1` JSON object.

The digest contract is `sha256-canonical-json-v1`.

For v1, canonical bytes are produced by the Python standard-library JSON
encoder with:

- `ensure_ascii=False`
- `sort_keys=True`
- `separators=(",", ":")`
- `allow_nan=False`
- UTF-8 encoding of the resulting string

Duplicate JSON object keys must be rejected during parsing. A parser that
silently applies last-key-wins behavior does not satisfy this contract.

Unicode strings are not normalized before hashing.

JSON numbers keep the representation produced by the Python parser and encoder.
Therefore `1` and `1.0` are distinct in v1, as are `0.0` and `-0.0`.

The digest is SHA-256 over the canonical UTF-8 bytes and is represented as
`sha256:<lowercase hexadecimal digest>`.

`sha256-canonical-json-v1` is intentionally bound to the current Python
implementation. Another language must reproduce the same canonical bytes or use
a new versioned digest contract.

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

## Integrity boundary

The digest provides deterministic content binding when the task is independently
recomputed and compared with the digest propagated through the local task
chain.

It is not a digital signature, MAC, provenance proof or tamper-evident log.

This contract does not claim protection against an actor that can modify the
task, review artifact, approval artifact and trusted runtime together. Its
purpose is to detect stale or mismatched task content across the governed
pipeline without treating the digest as authorization.

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

## Runtime implementation

PR129 implements this contract with:

1. one shared canonical task parser and digest helper;
2. strict duplicate-key rejection for `local-task/v1`;
3. `task_digest` emission from the review gate;
4. digest validation and propagation through the approval gate;
5. executor-side recomputation from the task used for command checks;
6. fail-closed `invalid` on missing, malformed or mismatched digest;
7. positive, canonicalization and mutation-negative tests.

PR129 does not broaden the PR127 command allowlist and does not make the digest
authorization, a signature, a MAC, a provenance proof or a tamper-evident log.
