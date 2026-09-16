# LAI Gateway quickstart

This guide installs and starts the current local-first LAI Gateway from source.
It is intentionally narrow: it helps a new operator verify the local stack without
claiming browser automation, n8n workflows, voice, broad MCP tool execution, or
social/career automation as ready-to-use features.

## Current scope

This quickstart covers:

- source checkout validation;
- editable local wrapper installation without `pip install`;
- non-secret configuration checks;
- Harness connectivity diagnostics;
- local loopback Gateway UI startup;
- first safe Workbench governance path using the restricted `local_status` adapter.

It does not cover a one-click installer, PyPI release, hosted service, cloud
model runtime, authenticated browser sessions, real n8n activation, broad MCP
execution, or external message/publication automation.

## Requirements

- Python 3.11 or newer.
- Bash-compatible shell.
- Git.
- Optional: Node.js, used by `make check` for static UI syntax validation.
- A compatible `lai harness` checkout available locally.
- A local LAI Harness control token file configured according to the Harness docs.

The Gateway basics require Harness 0.4.6 or newer. The Local Workbench routes
require Harness 0.5.0 or newer. When the Harness checkout has a different local
directory name, pass it explicitly with `--harness-repo`.

## 1. Clone or enter the source checkout

Use any local parent directory. Keep Gateway and Harness as separate checkouts.
Example layout:

```bash
/path/to/workspace/lai-gateway
/path/to/workspace/lai-harness-checkout
```

Enter the Gateway checkout:

```bash
cd /path/to/workspace/lai-gateway
git status --short
```

Expected result for a clean checkout:

```text
(no output)
```

## 2. Install local wrappers

The current alpha path is source-first. Install wrapper scripts into
`$HOME/.local/bin` without copying tokens and without printing secrets:

```bash
scripts/install-local.sh
```

Make sure the install directory is on `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify the wrapper:

```bash
lai-gateway --version
lai-gateway config
```

`config` prints paths and non-secret settings. It must not print token values.

## 3. Validate Gateway locally

Run the dependency-free validation suite before treating the checkout as usable:

```bash
PYTHON=python3 make check
```

Expected result:

```text
OK
```

If Node.js is unavailable, the JS syntax check is skipped by `make check`. That
is acceptable for a local smoke pass, but public release gates should run it.

## 4. Check Harness compatibility

Run a read-only Gateway/Harness compatibility check. Replace the Harness path
with your actual checkout:

```bash
lai-gateway-stack-check \
  --harness-repo /path/to/workspace/lai-harness-checkout \
  --target-gateway 0.1.34 \
  --min-harness 0.4.6
```

Machine-readable form:

```bash
lai-gateway-stack-check \
  --harness-repo /path/to/workspace/lai-harness-checkout \
  --target-gateway 0.1.34 \
  --min-harness 0.4.6 \
  --json
```

This check is read-only. It validates version compatibility, required Harness
contract capabilities, and non-executing MCP policy metadata. It does not start
servers, call MCP tools, publish releases, or send messages.

## 5. Diagnose the local runtime

Run:

```bash
lai-gateway doctor
lai-gateway readiness
```

Common outcomes:

| Symptom | Meaning | Next step |
| --- | --- | --- |
| missing token | Harness control token is not configured | configure it through the Harness setup path |
| Harness connection refused | `lai serve` is not running | start Harness on loopback |
| contract mismatch | Harness is too old or incompatible | update or point to the compatible Harness checkout |
| model unavailable | local model runtime is not ready | use `lai-gateway model-status` and `lai-gateway model-plan` |
| private bind rejected | unsafe bind address | keep loopback unless explicitly configuring private LAN mode |

No diagnostic command should print raw token values, pair tokens, chat ids, or
MCP credential values.

## 6. Start Harness on loopback

From the Harness checkout, start the control plane:

```bash
cd /path/to/workspace/lai-harness-checkout
lai serve --bind 127.0.0.1 --port 8765
```

Keep this process running. The Gateway expects Harness at
`http://127.0.0.1:8765` unless configured otherwise.

## 7. Start the Gateway UI

In another terminal, from the Gateway checkout:

```bash
cd /path/to/workspace/lai-gateway
lai-gateway dev --bind 127.0.0.1 --port 8787 --no-open
```

Then open:

```text
http://127.0.0.1:8787/
```

Alternative checked startup path:

```bash
lai-gateway stack-start \
  --harness-repo /path/to/workspace/lai-harness-checkout \
  --gateway-port 8787 \
  --skip-model \
  --open
```

Use `--check-only` to print the planned startup commands without starting any
service:

```bash
lai-gateway stack-start --check-only --harness-repo /path/to/workspace/lai-harness-checkout
```

## 8. First safe Workbench path

In the Local Workbench:

1. Confirm status/readiness.
2. Use normal chat for conversation-first responses.
3. Use the Governance panel to inspect approval capture, validation, effective authorization, and dispatcher state.
4. Execute only the explicitly named `local_status` safe dispatch path when you intend to test the first adapter.

The `local_status` adapter is a restricted in-process local handler. It does not
prove general adapter authorization and does not enable browser, n8n, voice, MCP
tool calls, filesystem access, or external side effects.

## 9. Public-alpha boundary

A successful quickstart means the current source checkout can be installed,
checked, diagnosed, and opened locally by a technical operator. It does not mean
LAI is a finished product.

Before a public alpha announcement, the project still needs the remaining roadmap
gates in `docs/product/roadmap.md`, especially identity tests, authorization
non-dry-run, restart recovery, model fallback, memory context, and restricted
local document text handling.

## Troubleshooting checklist

Run these commands and compare their output before filing an issue:

```bash
lai-gateway --version
lai-gateway config
lai-gateway doctor
lai-gateway readiness
lai-gateway model-status
lai-gateway stack-start --check-only --harness-repo /path/to/workspace/lai-harness-checkout
lai-gateway-stack-check --harness-repo /path/to/workspace/lai-harness-checkout --target-gateway 0.1.34 --min-harness 0.4.6
```

Useful references:

- `README.md` for current scope.
- `docs/product/index.md` for canonical product documentation.
- `docs/product/implementation_matrix.md` for implemented versus contract-only areas.
- `docs/product/alpha_readiness.md` for public alpha go/no-go criteria.
- `docs/MODEL_OPS.md` for local model diagnostics.
- `docs/MOBILE_OPS.md` for private LAN/mobile operation.
- `docs/RELEASE.md` for release governance.
