#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
harness_repo=${LAI_HARNESS_REPO:-"$(dirname -- "$repo_dir")/lai-local-agent"}
target_gateway=${LAI_GATEWAY_TARGET_VERSION:-}
target_harness=${LAI_HARNESS_TARGET_VERSION:-0.4.6}
json_mode=0

events_file=""
release_err=""

usage() {
  cat <<'USAGE'
Usage: stack-check.sh [--harness-repo PATH] [--target-gateway VERSION] [--target-harness VERSION] [--json]

Runs a local, read-only compatibility check for lai-gateway and lai harness.
It validates versions, the harness gateway contract, the non-executing MCP
foundation, and gateway release-check version/safety signals. A dirty checkout is
reported but allowed because this script is intended for pre-commit validation.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness-repo)
      [ "$#" -ge 2 ] || { echo "--harness-repo requires a value" >&2; exit 2; }
      harness_repo=$2
      shift 2
      ;;
    --target-gateway)
      [ "$#" -ge 2 ] || { echo "--target-gateway requires a value" >&2; exit 2; }
      target_gateway=$2
      shift 2
      ;;
    --target-harness)
      [ "$#" -ge 2 ] || { echo "--target-harness requires a value" >&2; exit 2; }
      target_harness=$2
      shift 2
      ;;
    --json)
      json_mode=1
      shift
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cleanup() {
  [ -z "$events_file" ] || rm -f "$events_file"
  [ -z "$release_err" ] || rm -f "$release_err"
}
trap cleanup EXIT

events_file=$(mktemp -t lai-gateway-stack-check.XXXXXX)

append_event() {
  local status=$1
  local name=$2
  local detail=${3:-}
  STACK_EVENT_STATUS="$status" STACK_EVENT_NAME="$name" STACK_EVENT_DETAIL="$detail" \
    "$python_bin" - <<'PY' >>"$events_file"
import json
import os

print(json.dumps({
    "status": os.environ["STACK_EVENT_STATUS"],
    "name": os.environ["STACK_EVENT_NAME"],
    "detail": os.environ.get("STACK_EVENT_DETAIL", ""),
}, sort_keys=True))
PY
}

print_event() {
  local status=$1
  local name=$2
  local detail=${3:-}
  append_event "$status" "$name" "$detail"
  if [ "$json_mode" -eq 1 ]; then
    return
  fi
  case "$status" in
    ok) echo "ok: $name${detail:+ $detail}" ;;
    note) echo "note: $name${detail:+ $detail}" ;;
    fail) echo "error: $name${detail:+ $detail}" >&2 ;;
  esac
}

print_json_summary() {
  local overall=$1
  STACK_EVENTS_FILE="$events_file" STACK_OVERALL="$overall" \
    STACK_GATEWAY_VERSION="${gateway_version:-}" STACK_HARNESS_VERSION="${harness_version:-}" \
    STACK_TARGET_GATEWAY="${target_gateway:-}" STACK_TARGET_HARNESS="$target_harness" \
    STACK_GATEWAY_REPO="$repo_dir" STACK_HARNESS_REPO="$harness_repo" \
    "$python_bin" - <<'PY'
import json
import os
from pathlib import Path

checks = []
path = Path(os.environ["STACK_EVENTS_FILE"])
if path.exists():
    checks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(json.dumps({
    "overall": os.environ["STACK_OVERALL"],
    "product": "lai-gateway-stack",
    "gateway_version": os.environ.get("STACK_GATEWAY_VERSION") or None,
    "harness_version": os.environ.get("STACK_HARNESS_VERSION") or None,
    "target_gateway": os.environ.get("STACK_TARGET_GATEWAY") or None,
    "target_harness": os.environ.get("STACK_TARGET_HARNESS") or None,
    "gateway_repo": os.environ.get("STACK_GATEWAY_REPO") or None,
    "harness_repo": os.environ.get("STACK_HARNESS_REPO") or None,
    "checks": checks,
}, ensure_ascii=False, indent=2, sort_keys=True))
PY
}

fail() {
  print_event fail stack_check "$*"
  if [ "$json_mode" -eq 1 ]; then
    print_json_summary blocked
  fi
  exit 1
}

run_gateway_py() {
  (
    cd "$repo_dir"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo_dir${PYTHONPATH:+:$PYTHONPATH}" \
      "$python_bin" "$@"
  )
}

run_harness() {
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$harness_repo/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$python_bin" "$harness_repo/src/local-agent" "$@"
}

[ -d "$repo_dir/lai_gateway" ] || fail "gateway package not found at $repo_dir"
[ -f "$harness_repo/src/local-agent" ] || fail "harness local-agent not found at $harness_repo/src/local-agent"

gateway_version=$(run_gateway_py - <<'PY'
from lai_gateway import __version__
print(__version__)
PY
)
target_gateway=${target_gateway:-$gateway_version}
[ "$gateway_version" = "$target_gateway" ] || fail "gateway version $gateway_version does not match target $target_gateway"
print_event ok gateway_version "$gateway_version"

harness_version_text=$(run_harness --version)
harness_version=${harness_version_text##* }
[ "$harness_version" = "$target_harness" ] || fail "harness version $harness_version does not match target $target_harness"
print_event ok harness_version "$harness_version"

contract_json=$(run_harness --gateway-contract --json)
printf '%s' "$contract_json" | run_gateway_py -c 'import json, sys; from lai_gateway.contract import validate_gateway_contract; validate_gateway_contract(json.load(sys.stdin))'
print_event ok gateway_contract_compatible

mcp_status_json=$(run_harness --mcp status --json)
printf '%s' "$mcp_status_json" | TARGET_HARNESS="$target_harness" run_gateway_py -c '
import json, os, sys
payload = json.load(sys.stdin)
assert payload["version"] == os.environ["TARGET_HARNESS"], payload.get("version")
assert payload["security"]["executes_tools"] is False
assert payload["security"]["prints_credentials"] is False
assert payload["security"]["reads_env_values"] is False
'
print_event ok harness_mcp_status_non_executing

policy_json=$(run_harness --mcp policy-check --operation call-tool --server desktop-commander --tool read_file --json)
printf '%s' "$policy_json" | run_gateway_py -c '
import json, sys
payload = json.load(sys.stdin)
assert payload["decision"] == "DENY", payload
assert payload["executed"] is False, payload
'
print_event ok harness_mcp_call_tool_denied

run_harness --mcp status --help >/dev/null
run_harness --mcp tools --help >/dev/null
run_harness --mcp policy-check --help >/dev/null
print_event ok harness_mcp_help_non_executing

release_err=$(mktemp -t lai-gateway-stack-release-check.XXXXXX)
set +e
release_json=$(run_gateway_py -m lai_gateway release-check --target "$target_gateway" --json 2>"$release_err")
release_rc=$?
set -e
printf '%s' "$release_json" | TARGET_GATEWAY="$target_gateway" RELEASE_RC="$release_rc" run_gateway_py -c '
import json, os, sys
payload = json.load(sys.stdin)
assert payload["target_version"] == os.environ["TARGET_GATEWAY"], payload.get("target_version")
checks = {check["name"]: check for check in payload.get("checks", [])}
assert checks["version_match"]["status"] == "ok", checks.get("version_match")
assert checks["release_safety"]["status"] == "ok", checks.get("release_safety")
assert payload.get("validation_command") == "make check; make milestone-gate", payload.get("validation_command")
assert payload.get("validation_commands") == ["make check", "make milestone-gate"], payload.get("validation_commands")
unexpected = [c for c in payload.get("checks", []) if c.get("status") == "fail" and c.get("name") != "git_status"]
assert not unexpected, unexpected
'
print_event ok gateway_release_check_version_and_safety
if [ "$release_rc" -ne 0 ]; then
  print_event note gateway_release_check_exit "$release_rc (dirty checkout is acceptable before local commit)"
fi

if [ "$json_mode" -eq 1 ]; then
  print_json_summary ready_for_local_commit
else
  echo "overall: ready_for_local_commit"
fi
