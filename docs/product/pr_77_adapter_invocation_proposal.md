# PR 77 — Adapter invocation proposal

## Goal

Introduce a read-only adapter invocation proposal object. The proposal binds an adapter,
requested capability, normalized action context, policy evaluation, and authorization
envelope before any adapter execution exists.

## Scope

This PR adds a proposal surface only. It does not execute adapters, dispatch tools,
open browsers, run n8n workflows, capture audio, process media, publish content,
or persist authorization records.

## Contract

An invocation proposal must include:

- proposal id
- proposal status
- requested capability
- adapter id
- actor
- channel
- domain
- action
- bounded public parameters
- permission decision
- policy evaluation
- authorization record
- execution flags proving no execution can occur

## Required behavior

- Missing or unknown adapters fail closed.
- Undeclared capabilities fail closed.
- Declared but ungranted capabilities require authorization.
- Secret-shaped parameter values are redacted before rendering or JSON output.
- Authorization records remain non-effective in this PR.
- Adapter invocation proposals are read-only and do not grant permission.

## Non-goals

- No adapter runtime.
- No approval capture.
- No authorization persistence.
- No adapter dispatch.
- No filesystem/network/browser/n8n/voice/media/social side effects.

## Validation

- Unit tests cover blocked and approval-required proposal states.
- CLI output is JSON/text and secret-free.
- Gateway endpoint is read-only, private-mode protected, and secret-free.
- Full repository check must pass.
