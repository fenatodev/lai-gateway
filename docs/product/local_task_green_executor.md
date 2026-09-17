# Local task green executor

Status: implemented by PR127.

`local-task-green-executor/v1` is the first bounded local executor for LAI green-zone local task commands.

It is intentionally narrow:

- it only accepts tasks that passed `local-task-approval-gate/v1` as `ready_without_approval`;
- it only accepts `local-task/v1` task records with `autonomy_zone = green`;
- it blocks any task requiring human approval;
- it executes no shell string and routes process execution through `tool_mediation.run_process`; this preserves the `shell=False` boundary via mediated argv execution;
- it only runs commands that are both present in the task record and exactly allowlisted by the executor;
- it does not call Harness, tools, adapters, browser automation, n8n, credentials, messages, publication or merge flows;
- it does not issue or consume permission grants.

## Contract

Input:

- repository-relative approval gate JSON file;
- repository-relative task JSON file;
- optional command list; when omitted, commands are derived from `task.proposed_commands`;
- explicit `--execute` flag for actual execution.

Output:

- `ready` when the command set is valid but `--execute` was not supplied;
- `executed` when every allowlisted command exits with code 0;
- `failed` when an allowlisted command ran and returned non-zero;
- `blocked` for non-green, approval-required, non-allowlisted, non-task-declared or unsafe requests;
- `invalid` for malformed paths, JSON, schema or mismatched task identity.

## Security limits

This executor is not general shell access. It is a deterministic local command runner for a fixed allowlist.

The executor may run local validation commands, but it must not:

- run arbitrary shell;
- expand permissions;
- use secrets or credentials;
- send messages;
- publish content;
- submit forms;
- purchase anything;
- merge to `main`;
- call Harness;
- dispatch adapters;
- invoke external tools;
- perform authenticated browser automation.

## Initial allowlist

PR127 starts with a minimal validation-oriented allowlist:

- `git --version`
- `git diff --check`
- `git status --short --branch`
- `git diff --stat`
- `python3 -m compileall -q lai_gateway tests`
- `python3 -m unittest tests.test_local_task_review_gate -v`
- `python3 -m unittest tests.test_local_task_approval_gate -v`
- `python3 -m unittest tests.test_local_task_green_executor -v`
- `python3 -m unittest tests.test_product_docs -v`
- `make check`

The allowlist is deliberately exact. Broader command families require later PRs.
