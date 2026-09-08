#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"
DOGFOOD_MODE="${LAI_GATEWAY_DOGFOOD_MODE:-diagnose}"
DOGFOOD_TASK="${LAI_GATEWAY_DOGFOOD_TASK:-Read-only status check: report branch, git clean state, MCP broker readiness, execution policy, and model endpoint. Do not inspect files.}"
POLL_LIMIT="${LAI_GATEWAY_DOGFOOD_POLL_LIMIT:-12}"
POLL_SECONDS="${LAI_GATEWAY_DOGFOOD_POLL_SECONDS:-2}"

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

run_gateway() {
  "$PYTHON_BIN" -m lai_gateway "$@"
}

scan_json() {
  local label="$1"
  local path="$2"
  "$PYTHON_BIN" - "$label" "$path" <<'PY'
import json
import re
import sys

label, path = sys.argv[1], sys.argv[2]
raw = open(path, encoding="utf-8").read()
payload = json.loads(raw)
forbidden_keys = {"stdout", "stderr", "task", "task_text", "transcript", "transcripts", "turn", "turns", "repository", "workspace_path", "root_path", "cwd", "metrics_file", "audit_file"}
found = []

def walk(value, trail=""):
    if isinstance(value, dict):
        for key, nested in value.items():
            next_trail = f"{trail}.{key}" if trail else str(key)
            if str(key).lower() in forbidden_keys:
                found.append(next_trail)
            walk(nested, next_trail)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, f"{trail}[{index}]")

walk(payload)
secret_shape = bool(re.search(r"Bearer\s+\S+|chat_id|pair_token|/home/[^\s\"]+|/mnt/[A-Za-z]/Users/[^\s\"]+|[A-Za-z]:\\\\Users\\\\[^\s\"]+|[0-9]{9}:[A-Za-z0-9_-]{20,}", raw))
if found or secret_shape:
    print(f"{label}: unsafe payload")
    print(f"forbidden_keys={found}")
    print(f"secret_shape={secret_shape}")
    raise SystemExit(1)
print(f"{label}: sanitized")
PY
}

echo "mobile-readonly-dogfood: start"

# Prove write-capable modes are rejected before any run is accepted.
if run_gateway runs create --mode implement --task "must be rejected" >"$tmp_dir/write.out" 2>"$tmp_dir/write.err"; then
  echo "write-mode rejection: failed"
  exit 1
fi
if ! grep -q "invalid choice\|mode must be read-only\|write_mode_not_allowed" "$tmp_dir/write.err" "$tmp_dir/write.out" 2>/dev/null; then
  echo "write-mode rejection: unexpected error"
  exit 1
fi
echo "write-mode rejection: ok"

run_gateway sessions create >"$tmp_dir/session-create.json"
scan_json "session-create" "$tmp_dir/session-create.json"
session_id="$($PYTHON_BIN - "$tmp_dir/session-create.json" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
print((p.get("session") or {}).get("session_id") or p.get("session_id") or "")
PY
)"
if [[ ! "$session_id" =~ ^cs-[0-9a-f]{16}$ ]]; then
  echo "session id: invalid"
  exit 1
fi
echo "session id: ok"

run_gateway runs create --mode "$DOGFOOD_MODE" --session-id "$session_id" --task "$DOGFOOD_TASK" >"$tmp_dir/run-create.json"
scan_json "run-create" "$tmp_dir/run-create.json"
run_id="$($PYTHON_BIN - "$tmp_dir/run-create.json" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
r=p.get("run") or p
print(r.get("control_run_id") or r.get("run_id") or "")
PY
)"
if [[ ! "$run_id" =~ ^cr-[0-9a-f]{16}$ ]]; then
  echo "run id: invalid"
  exit 1
fi
echo "run id: ok"

status=""
for _ in $(seq 1 "$POLL_LIMIT"); do
  run_gateway runs get "$run_id" >"$tmp_dir/run-get.json"
  scan_json "run-get" "$tmp_dir/run-get.json"
  status="$($PYTHON_BIN - "$tmp_dir/run-get.json" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
r=p.get("run") or p
print(r.get("status") or "")
PY
)"
  case "$status" in
    succeeded|completed|failed|cancelled) break ;;
  esac
  sleep "$POLL_SECONDS"
done
if [[ "$status" != "succeeded" && "$status" != "completed" ]]; then
  echo "run status: $status"
  exit 1
fi
echo "run status: $status"

run_gateway runs events "$run_id" >"$tmp_dir/run-events.json"
scan_json "run-events" "$tmp_dir/run-events.json"
event_count="$($PYTHON_BIN - "$tmp_dir/run-events.json" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
print(len(p.get("events") or []))
PY
)"
if [ "$event_count" -lt 1 ]; then
  echo "run events: missing"
  exit 1
fi
echo "run events: $event_count"

run_gateway sessions get "$session_id" >"$tmp_dir/session-get.json"
scan_json "session-get" "$tmp_dir/session-get.json"
run_gateway sessions delete "$session_id" >"$tmp_dir/session-delete.json"
scan_json "session-delete" "$tmp_dir/session-delete.json"
echo "session cleanup: ok"
echo "mobile-readonly-dogfood: ready"
