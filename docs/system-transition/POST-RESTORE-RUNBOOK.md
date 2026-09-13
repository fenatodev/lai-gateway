# Post-restore runbook

Use this after disk, firmware, bootloader, or OS work to decide whether LAI is ready for development again.

## 1. Repository check

From the restored Gateway repository:

```bash
git status --short --branch
git log --oneline -5
```

Expected:

- branch is `main`;
- state is clean;
- latest commit is at least `7c37c3a`.

From the restored Harness repository:

```bash
git status --short --branch
git log --oneline -5
```

Expected:

- branch is `main`;
- state is clean;
- latest commit is at least `eb5d495`.
## 2. Install wrappers

From Gateway:

```bash
./scripts/install-local.sh
lai-gateway --version
```

From Harness:

```bash
./scripts/install-local.sh
lai --version
```

Expected versions:

- Gateway `0.1.34` or newer.
- Harness `0.5.0` or newer.

## 3. Start the stack

Use the existing stack starter and the restored Harness repository path.

Expected result:

- model server ready;
- Harness ready;
- Gateway ready;
- Gateway UI reachable on the local machine.
## 4. Smoke tests

Run these checks before resuming UI implementation:

```bash
make check
lai-gateway model-status --probe-openai --json
lai-gateway model-smoke --json
lai-gateway model-task --json
```

Expected:

- tests pass;
- model status is ready;
- smoke/task checks complete without exposing secrets.

## 5. Manual UI check

Open the local Gateway UI and verify:

- Workbench shell loads first-level controls cleanly;
- Debug is collapsed by default;
- Send button is enabled only when no run is active;
- Cancel button is disabled when no run is active;
- mode/context changes do not reuse stale review state.
