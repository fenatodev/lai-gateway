# PR129 - Local task content binding runtime

PR129 implements the `local-task-content-binding/v1` contract specified by
PR128.

## Objective

Bind the exact parsed `local-task/v1` content across review, approval
classification and bounded green execution.

`task_id` remains correlation only. `task_digest` provides deterministic
content binding and never grants authority.

## Runtime changes

PR129 may:

- add one shared local task content-binding module;
- reject duplicate JSON object keys when parsing `local-task/v1`;
- compute `sha256-canonical-json-v1` from the parsed task object;
- emit `task_digest` from `local-task-review-gate/v1`;
- require and propagate the same valid digest through
  `local-task-approval-gate/v1`;
- recompute the digest in `local-task-green-executor/v1`;
- require the recomputed digest to equal the approval-gate digest before
  execution;
- expose the digest in machine-readable gate/executor output;
- add positive and mutation-negative tests.

## Shared digest rules

The implementation must use one shared helper for canonical bytes and digest
generation.

For v1:

- Python standard-library JSON serialization is authoritative;
- `ensure_ascii=False`;
- `sort_keys=True`;
- `separators=(",", ":")`;
- `allow_nan=False`;
- output encoded as UTF-8;
- digest formatted as `sha256:` plus 64 lowercase hexadecimal characters;
- duplicate JSON object keys are rejected before hashing;
- Unicode is not normalized;
- `1` and `1.0` remain distinct;
- `0.0` and `-0.0` remain distinct.

## Gate behavior

Review:

- derives `task_digest` from the parsed task;
- fails invalid if the task cannot be parsed or canonicalized according to v1;
- keeps all existing authority and autonomy checks.

Approval:

- requires `task_digest` in review input;
- rejects missing or malformed digest as invalid;
- carries the exact reviewed digest to its output;
- does not recompute task content because it does not receive the task.

Executor:

- requires a valid approval `task_digest`;
- computes the digest from the same parsed task record used for command checks;
- requires exact digest equality before execution;
- treats mismatch as invalid, not `needs_approval`;
- never executes when content binding fails.

## Tests

PR129 must cover at least:

- stable digest across object key order;
- insignificant source whitespace producing the same parsed-task digest;
- `1` versus `1.0`;
- `0.0` versus `-0.0`;
- non-normalized Unicode distinction;
- duplicate object-key rejection;
- review emits a valid digest;
- approval rejects missing or malformed digest;
- approval preserves the reviewed digest;
- executor accepts unchanged reviewed content;
- executor rejects task mutation with unchanged `task_id`;
- rejected mutation executes no command.

## Boundaries

PR129 must not:

- expand `_ALLOWED_EXACT_COMMANDS`;
- add arbitrary shell access;
- bind `local-task-outbox/v1`;
- create or consume grants;
- change autonomy-zone semantics;
- remove human approval requirements;
- call Harness;
- add adapter or tool dispatch;
- use credentials;
- send messages;
- publish;
- automate merge to `main`;
- claim signature, MAC, provenance or tamper-evident guarantees.
