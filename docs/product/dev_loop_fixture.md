# Dev loop fixture

`dev-loop-fixture/v1` is the controlled local development loop fixture introduced after `approval-inbox/v1`.

It models the LAI Observe/Work/Review/Apply path over a sanitized pending approval record, without turning that record into operational authority.

## Contract

Input must come from an explicit project workspace and a local approval inbox file.

The fixture may read sanitized pending approval metadata and produce deterministic evidence for these phases:

- observe: inspect the pending approval envelope.
- work: prepare a fixture-only local work plan.
- review: produce bounded review evidence.
- apply: simulate apply inside the fixture only; the source checkout remains unchanged.

## Non-authority

The fixture never grants permission, never creates effective authorization, never issues or consumes grants, never dispatches adapters, never calls Harness and never executes tools.

It rejects browser, n8n, broad MCP, credentials, messaging, publication, grant, adapter, tool, Harness, deploy, release and merge-shaped requests.

## Data touched

The fixture reads only the explicit approval inbox file inside the explicit workspace. It does not scan HOME, does not recurse, does not ingest files implicitly and does not write source checkout files.
