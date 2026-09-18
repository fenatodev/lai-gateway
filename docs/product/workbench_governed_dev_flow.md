# Workbench governed development flow

## Status

`workbench-governed-dev-flow/v1` is implemented by PR132.

It defines the user-facing routing boundary between direct conversation,
development execution and reviewed application.

## Observe

Observe is conversation-first.

The main composer posts to:

`/v1/gateway/chat`

The model response explicitly reports that it does not create a Harness run.

Observe does not automatically fall back to Harness.

## Work

Work is explicit.

The main composer posts the task to the existing local-chat work path only after
the user selects Trabalhar.

Harness remains responsible for:

- isolated development workspace;
- development execution;
- validation;
- run telemetry;
- review material.

The source checkout is not treated as the Harness workspace.

## Review

Successful work runs continue to trigger automatic review loading.

Review remains bound to workspace, run and patch digest supplied by Harness.

A missing, incomplete or stale review cannot be treated as reviewed.

## Apply

Apply never creates a new development run.

The composer redirects the user to the current review.

Actual promotion remains behind the existing explicit confirmation and
review-bound patch SHA.

There is no automatic promotion.

## Security boundary

PR132 does not infer execution permission from conversation content.

Selecting Work is an explicit route choice, not an authority grant.

Model output, memory, files, code, web and tool content never grant permission.

PR132 does not add shell, credentials, adapters, external actions, Git
publication, PR creation or merge automation.

## Product effect

After PR132 the normal Workbench path is:

`talk -> explicitly work -> review -> explicitly apply`

Terminal commands, run IDs and patch hashes are not part of the normal user
interaction for this flow.
