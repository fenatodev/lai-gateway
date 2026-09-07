# Release governance

`lai-gateway` starts with a deliberately small release process. The gateway is a companion adapter around `lai harness`; it must not gain hidden publication authority just because publishing things makes dashboards feel productive.

## Stable release checklist

Before tagging a release:

1. Merge changes through a pull request into protected `main`.
2. Wait for required GitHub checks to pass on `main`.
3. Run `make check` locally from a clean checkout.
4. Run `make milestone-gate HARNESS_REPO=/path/to/lai-local-agent TARGET_GATEWAY=X.Y.Z MIN_HARNESS=0.4.6` for Gateway/Harness compatibility.
5. Run `python3 -m lai_gateway release-check --target X.Y.Z --json`.
5. Create an annotated tag only when the release check reports `phase=ready_to_tag`.
6. Push the tag and verify tag CI.
7. Create a stable GitHub release with `prerelease=false`.

## Current release command

```bash
python3 -m lai_gateway release-check --target 0.1.0 --json
```

The command is read-only. It checks version alignment, git cleanliness, protected-main integration state, expected tag state, and the validation command. It does not create tags, push commits, upload artifacts, call the model, or publish releases.

## Manual boundaries

The first gateway release is source-only. Do not add PyPI publication, binary artifacts, remote run creation, Telegram delivery, public bind support, or token brokerage to the release process until those capabilities have their own threat model and tests.
