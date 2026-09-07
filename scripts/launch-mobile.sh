#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
candidate_ip=${LAI_GATEWAY_MOBILE_IP:-}
port=${LAI_GATEWAY_MOBILE_PORT:-8787}
telegram_notify=0
show_pair=0

usage() {
  cat <<USAGE
usage: lai-gateway-mobile --candidate-ip <private-ip> [--port 8787] [--telegram-notify] [--show-pair]

Idempotent mobile launcher:
  - if mobile gateway is already ready, prints ops-status and exits
  - if listener is active but pair token is stale, repairs tokens and exits
  - if listener is absent, prepares tokens then starts mobile-serve

No token values are printed unless --show-pair is explicitly passed from an interactive terminal.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --candidate-ip)
      candidate_ip=${2:?--candidate-ip requires a value}
      shift 2
      ;;
    --port)
      port=${2:?--port requires a value}
      shift 2
      ;;
    --telegram-notify)
      telegram_notify=1
      shift
      ;;
    --show-pair)
      show_pair=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$show_pair" = "1" ] && [ ! -t 1 ] && [ "${LAI_GATEWAY_ALLOW_NONINTERACTIVE_SHOW_PAIR:-0}" != "1" ]; then
  echo "error: --show-pair requires an interactive terminal; refusing to print a pair token to a pipe or log" >&2
  exit 2
fi

if [ -z "$candidate_ip" ]; then
  echo "error: --candidate-ip is required, or set LAI_GATEWAY_MOBILE_IP" >&2
  exit 2
fi

cd "$repo_dir"
status_json=$("$python_bin" -m lai_gateway mobile-status --candidate-ip "$candidate_ip" --port "$port" --json 2>/dev/null || true)
overall=$(STATUS_JSON="$status_json" "$python_bin" - <<'PYCODE'
import json, os
try:
    payload = json.loads(os.environ.get("STATUS_JSON", ""))
except json.JSONDecodeError:
    payload = {}
print(payload.get("overall", "unknown"))
PYCODE
)
listener=$(STATUS_JSON="$status_json" "$python_bin" - <<'PYCODE'
import json, os
try:
    payload = json.loads(os.environ.get("STATUS_JSON", ""))
except json.JSONDecodeError:
    payload = {}
print("1" if payload.get("listener", {}).get("active") else "0")
PYCODE
)

repair_args=(mobile-repair --candidate-ip "$candidate_ip" --port "$port" --prepare)
serve_args=(mobile-serve --candidate-ip "$candidate_ip" --port "$port")
if [ "$show_pair" = "1" ]; then
  repair_args+=(--show-pair)
  serve_args+=(--show-pair)
fi
if [ "$telegram_notify" = "1" ]; then
  repair_args+=(--telegram-notify)
  serve_args+=(--telegram-notify)
fi

if [ "$listener" = "1" ]; then
  if [ "$overall" != "ready" ]; then
    "$python_bin" -m lai_gateway "${repair_args[@]}"
  fi
  exec "$python_bin" -m lai_gateway ops-status --candidate-ip "$candidate_ip" --port "$port"
fi

if [ "$overall" = "needs_prepare" ] || [ "$overall" = "needs_pair" ] || [ "$overall" = "unknown" ]; then
  "$python_bin" -m lai_gateway mobile-repair --candidate-ip "$candidate_ip" --port "$port" --prepare
fi
exec "$python_bin" -m lai_gateway "${serve_args[@]}"
