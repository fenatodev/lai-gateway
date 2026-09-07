# lai-gateway — Agent Instructions

lai-gateway is the companion control surface for `lai harness`. Keep it small, local-first, private-by-default, and aligned with the Harness contract.

## Operating mode

`docs/OPERATING-MODE.md` is the canonical Gateway operating policy. Follow it unless a higher-priority instruction or safety rule says otherwise.

Before any action, prefer product progress over work movement. Before ending a session, synchronizing, opening a PR, or publishing, check whether another bounded, directly related deliverable can be concluded from the current context without scope creep.

## Development workflow

- Work on a dedicated milestone branch.
- Make small local commits for coherent, tested slices.
- Use focused tests first and `make check` when changes cross subsystems.
- Use `make milestone-gate` at milestone freeze, not after every edit.
- Keep version bump, PR, tag, and release work at milestone boundaries.
- Prefer minimum-version plus capability/contract compatibility over patch-exact Harness coupling when the contract is backward compatible.

## Safety rules

- Do not expose tokens, pairing codes, chat IDs, local paths, or private runtime state.
- Keep private mode authenticated and fail-closed.
- Do not add write-capable Harness operations, shell execution, MCP tool execution, browser automation, downloads, or token persistence without a dedicated threat model and tests.
- Never weaken tests solely to make faulty implementation code pass.
