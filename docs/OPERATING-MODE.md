# lai-gateway Operating Mode

This is the canonical operating policy for day-to-day Gateway development and companion alignment with `lai harness`.

## Intent

Optimize for durable product progress, not release ritual.

The Gateway should support Harness capabilities through stable contracts, focused local feedback, and milestone batching. It should not require a public Gateway release only because the Harness patch number changed when required routes, capabilities, and safety invariants remain compatible.

## Decision gate

Before any action, ask: does this generate real product progress, or does it merely move work around?

Prefer actions that close a user-visible gap, reduce future integration churn, improve private-mode safety, improve observability, or preserve current context in a deterministic artifact.

Before ending a session, synchronizing, opening a PR, or publishing, ask what bounded directly related deliverable can be concluded now so this area does not need to be revisited soon.

Stop when the next action is only scope creep, cosmetic cleanup, speculative architecture, or publication ritual.

## Development cadence

Use a dedicated milestone branch for related work. A milestone may contain multiple small local commits when each commit is coherent and validated by the cheapest trustworthy feedback loop.

During active development:

- inspect repository evidence before assuming behavior;
- run focused tests for touched behavior;
- run `make check` when changes cross Gateway subsystems;
- avoid `make milestone-gate` after every small edit;
- avoid version bumps and final release notes until milestone freeze unless the active branch is already a release-prep branch.

## Compatibility policy

Default to minimum supported Harness version plus live contract/capability validation when backward compatible.

Use exact `--target-harness` checks only for strict release audits, regression reproduction, or when the Gateway intentionally depends on a specific Harness patch.

## Publication policy

Push, PR, tag, and release only for coherent integration batches or user-installable milestones. Do not publish for ordinary doc cleanup, renamed tests, or target-number churn when capability-based compatibility already passes.
