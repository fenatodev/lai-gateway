#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
host=${LAI_GATEWAY_MODEL_HOST:-}
port=${LAI_GATEWAY_MODEL_PORT:-18082}
model_path=${LAI_GATEWAY_MODEL_PATH:-}
model_name=${LAI_GATEWAY_MODEL_NAME:-}
key_file=${LAI_GATEWAY_MODEL_API_KEY_FILE:-}
threads=${LAI_GATEWAY_MODEL_THREADS:-8}
ctx_size=${LAI_GATEWAY_MODEL_CTX_SIZE:-4096}
gpu_layers=${LAI_GATEWAY_MODEL_GPU_LAYERS:-0}
create_key=0
force_key=0
plan_only=0
probe_only=0
foreground=0
ephemeral=0
run_smoke=0
run_task=0
run_eval=0
run_record=0
task_name=code-mini
explicit_runtime=0
for runtime_var in \
  LAI_GATEWAY_MODEL_HOST LAI_GATEWAY_MODEL_PORT LAI_GATEWAY_MODEL_PATH \
  LAI_GATEWAY_MODEL_NAME LAI_GATEWAY_MODEL_API_KEY_FILE \
  LAI_GATEWAY_MODEL_THREADS LAI_GATEWAY_MODEL_CTX_SIZE LAI_GATEWAY_MODEL_GPU_LAYERS; do
  if [ -n "${!runtime_var:-}" ]; then
    explicit_runtime=1
  fi
done

usage() {
  cat <<USAGE
usage: lai-gateway-model [--host <windows-wsl-ip>] [--port 18082] [--model-path <gguf>] [--model-name <name>] [--key-file <path>] [--create-key] [--force-key] [--plan-only] [--probe-only] [--smoke] [--task [code-mini]] [--eval] [--record] [--foreground] [--ephemeral]

Idempotent local model launcher for Windows llama.cpp from WSL:
  - reuses an already configured healthy local endpoint when no runtime override is requested
  - discovers the recommended local GGUF when --model-path is omitted
  - creates/verifies a local model API key file without printing the key
  - starts llama-server.exe bound to a private WSL-reachable Windows IP
  - writes token-free model runtime config for later ops-status/model-status checks
  - waits for /v1/models, then runs lai-gateway model-status --probe-openai
  - with --smoke, also runs a fixed-prompt completion smoke test
  - with --task, also runs a fixed local model task such as code-mini
  - with --eval, runs the fixed smoke + task evaluation suite
  - with --record, writes prompt-free local model metrics for smoke/task/eval
  - with --ephemeral, stops only a model server started by this invocation after validation

No model downloads are performed. No API key values are printed.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      explicit_runtime=1
      host=${2:?--host requires a value}
      shift 2
      ;;
    --port)
      explicit_runtime=1
      port=${2:?--port requires a value}
      shift 2
      ;;
    --model-path)
      explicit_runtime=1
      model_path=${2:?--model-path requires a value}
      shift 2
      ;;
    --model-name)
      explicit_runtime=1
      model_name=${2:?--model-name requires a value}
      shift 2
      ;;
    --key-file)
      explicit_runtime=1
      key_file=${2:?--key-file requires a value}
      shift 2
      ;;
    --threads)
      explicit_runtime=1
      threads=${2:?--threads requires a value}
      shift 2
      ;;
    --ctx-size)
      explicit_runtime=1
      ctx_size=${2:?--ctx-size requires a value}
      shift 2
      ;;
    --gpu-layers)
      explicit_runtime=1
      gpu_layers=${2:?--gpu-layers requires a value}
      shift 2
      ;;
    --create-key)
      explicit_runtime=1
      create_key=1
      shift
      ;;
    --force-key)
      explicit_runtime=1
      create_key=1
      force_key=1
      shift
      ;;
    --plan-only)
      plan_only=1
      shift
      ;;
    --probe-only)
      probe_only=1
      shift
      ;;
    --smoke)
      run_smoke=1
      shift
      ;;
    --eval)
      run_eval=1
      shift
      ;;
    --record)
      run_record=1
      shift
      ;;
    --task)
      run_task=1
      if [ "${2:-}" != "" ] && [ "${2#--}" = "$2" ]; then
        task_name=$2
        shift 2
      else
        shift
      fi
      ;;
    --foreground)
      explicit_runtime=1
      foreground=1
      shift
      ;;
    --ephemeral)
      ephemeral=1
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

if [ "$foreground" = "1" ] && [ "$ephemeral" = "1" ]; then
  echo "error: --foreground and --ephemeral cannot be combined" >&2
  exit 2
fi

cd "$repo_dir"

json_get() {
  JSON_PAYLOAD=$1 "$python_bin" - "$2" <<'PYCODE'
import json, os, sys
payload = json.loads(os.environ.get('JSON_PAYLOAD') or '{}')
cur = payload
for part in sys.argv[1].split('.'):
    if isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
        break
print('' if cur is None else cur)
PYCODE
}

run_configured_validations() {
  "$python_bin" -m lai_gateway model-status --probe-openai
  record_args=()
  if [ "$run_record" = "1" ]; then
    record_args+=(--record)
  fi
  if [ "$run_eval" = "1" ]; then
    "$python_bin" -m lai_gateway model-eval "${record_args[@]}"
    return
  fi
  if [ "$run_smoke" = "1" ]; then
    "$python_bin" -m lai_gateway model-smoke "${record_args[@]}"
  fi
  if [ "$run_task" = "1" ]; then
    "$python_bin" -m lai_gateway model-task --task "$task_name" "${record_args[@]}"
  fi
}

if [ "$explicit_runtime" = "0" ] && [ "$plan_only" = "0" ]; then
  configured_status=$("$python_bin" -m lai_gateway model-status --probe-openai --json 2>/dev/null || true)
  if [ "$(json_get "$configured_status" overall)" = "ready" ]; then
    echo "lai-gateway-model: reusing configured ready endpoint"
    run_configured_validations
    exit 0
  fi
fi

if [ -z "$host" ]; then
  host=$("$python_bin" - <<'PYCODE'
from lai_gateway.model import _wsl_default_gateway
print(_wsl_default_gateway() or "")
PYCODE
)
fi
if [ -z "$host" ]; then
  echo "error: could not detect Windows WSL host IP; pass --host" >&2
  exit 2
fi

files_json=$("$python_bin" -m lai_gateway model-files --max-results 3 --json)
if [ -z "$model_path" ]; then
  model_path=$(json_get "$files_json" recommended.windows_path)
fi
if [ -z "$model_name" ]; then
  model_name=$(json_get "$files_json" recommended.name)
fi
if [ -z "$model_path" ] || [ -z "$model_name" ]; then
  echo "error: no recommended GGUF model found; run lai-gateway model-files" >&2
  exit 1
fi

if [ -z "$key_file" ]; then
  key_file=$("$python_bin" - "$model_path" <<'PYCODE'
import os, re, sys
path = sys.argv[1]
match = re.match(r"^([a-zA-Z]):\\Users\\([^\\]+)\\", path)
if match:
    print(f"/mnt/{match.group(1).lower()}/Users/{match.group(2)}/.config/lai-gateway/model-api-key")
else:
    match = re.match(r"^/mnt/([a-zA-Z])/Users/([^/]+)/", path)
    if match:
        print(f"/mnt/{match.group(1).lower()}/Users/{match.group(2)}/.config/lai-gateway/model-api-key")
    else:
        print(f"/mnt/c/Users/{os.environ.get('USER', 'user')}/.config/lai-gateway/model-api-key")
PYCODE
)
fi
key_file_win=$("$python_bin" - "$key_file" <<'PYCODE'
import re, sys
path = sys.argv[1]
match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", path)
if match:
    print(match.group(1).upper() + ':\\' + match.group(2).replace('/', '\\'))
else:
    print(path)
PYCODE
)
base_url="http://${host}:${port}"

if [ "$plan_only" = "1" ]; then
  echo "lai-gateway-model: plan"
  echo "host: $host"
  echo "port: $port"
  echo "model_name: $model_name"
  echo "model_path: $model_path"
  echo "key_file: $key_file"
  echo "base_url: $base_url"
  echo "start: llama-server.exe --host $host --port $port --model '<model-path>' --ctx-size $ctx_size --threads $threads --n-gpu-layers $gpu_layers --api-key-file '<key-file>' --cors-origins localhost --no-cors-credentials"
  echo "smoke: $run_smoke"
  echo "task: $run_task"
  echo "task_name: $task_name"
  echo "eval: $run_eval"
  echo "record: $run_record"
  exit 0
fi

if [ "$create_key" = "1" ]; then
  if [ "$force_key" = "1" ] || ! "$python_bin" -m lai_gateway model-key-check --path "$key_file" >/dev/null 2>&1; then
    key_args=(model-key-create --path "$key_file")
    if [ "$force_key" = "1" ]; then
      key_args+=(--force)
    fi
    "$python_bin" -m lai_gateway "${key_args[@]}"
  else
    "$python_bin" -m lai_gateway model-key-check --path "$key_file"
  fi
elif ! "$python_bin" -m lai_gateway model-key-check --path "$key_file" >/dev/null 2>&1; then
  echo "error: model API key file is not ready; run with --create-key or create one with lai-gateway model-key-create" >&2
  exit 1
fi

export LAI_GATEWAY_MODEL_BASE_URL="$base_url"
export LAI_GATEWAY_MODEL_NAME="$model_name"
export LAI_GATEWAY_MODEL_API_KEY_FILE="$key_file"

probe_models_endpoint() {
  "$python_bin" - "$base_url" "$key_file" <<'PYCODE'
import sys
import urllib.request
base_url, key_file = sys.argv[1:3]
try:
    key = open(key_file, encoding='utf-8').read().strip()
    request = urllib.request.Request(base_url.rstrip('/') + '/v1/models', headers={'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PYCODE
}

windows_listener_pid() {
  if ! command -v powershell.exe >/dev/null 2>&1; then
    return 0
  fi
  powershell.exe -NoProfile -Command     '$portNumber=[int]$args[0]; $hostName=$args[1]; $connection=Get-NetTCPConnection -State Listen -LocalPort $portNumber -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq $hostName } | Select-Object -First 1; if ($connection) { [Console]::Out.Write($connection.OwningProcess) }'     "$port" "$host" 2>/dev/null | tr -d '\r\n'
}

stop_windows_listener_pid() {
  local target_pid=${1:-}
  if [ -z "$target_pid" ] || ! command -v powershell.exe >/dev/null 2>&1; then
    return 0
  fi
  powershell.exe -NoProfile -Command \
    '$target=[int]$args[0]; Stop-Process -Id $target -Force -ErrorAction SilentlyContinue' \
    "$target_pid" >/dev/null 2>&1 || true
}

run_validations() {
  run_configured_validations
}

if [ "$probe_only" = "1" ]; then
  run_validations
  exit 0
fi

if ! command -v llama-server.exe >/dev/null 2>&1; then
  echo "error: llama-server.exe was not found from WSL PATH" >&2
  exit 1
fi

"$python_bin" - "$base_url" "$model_name" "$key_file" <<'PYCODE'
import sys
from lai_gateway.model import write_model_runtime_config
payload = write_model_runtime_config(base_url=sys.argv[1], model_name=sys.argv[2], api_key_file=sys.argv[3])
print(f"lai-gateway model-config: {payload['overall']}")
print("model_config_persisted: true")
print("stores_api_key_value: false")
PYCODE

if probe_models_endpoint; then
  run_validations
  exit 0
fi

if [ "$foreground" = "1" ]; then
  exec llama-server.exe \
    --host "$host" \
    --port "$port" \
    --model "$model_path" \
    --ctx-size "$ctx_size" \
    --threads "$threads" \
    --n-gpu-layers "$gpu_layers" \
    --api-key-file "$key_file_win" \
    --cors-origins localhost \
    --no-cors-credentials
fi

log_file="${TMPDIR:-/tmp}/lai-gateway-model-${port}.log"
rm -f "$log_file"
llama-server.exe \
  --host "$host" \
  --port "$port" \
  --model "$model_path" \
  --ctx-size "$ctx_size" \
  --threads "$threads" \
  --n-gpu-layers "$gpu_layers" \
  --api-key-file "$key_file_win" \
  --cors-origins localhost \
  --no-cors-credentials >"$log_file" 2>&1 &
pid=$!
windows_pid=""
cleanup_started_model() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
  if [ -n "${windows_pid:-}" ]; then
    stop_windows_listener_pid "$windows_pid"
  fi
}
if [ "$ephemeral" = "1" ]; then
  trap cleanup_started_model EXIT INT TERM
fi
echo "lai-gateway-model: starting"
echo "pid: $pid"
echo "base_url: $base_url"
echo "model_name: $model_name"
echo "log_file: $log_file"

ready=0
for _ in $(seq 1 90); do
  if probe_models_endpoint; then
    ready=1
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "error: llama-server exited before readiness" >&2
    tail -80 "$log_file" >&2 || true
    exit 1
  fi
  sleep 2
done

if [ "$ready" != "1" ]; then
  echo "error: llama-server did not become ready in time" >&2
  tail -80 "$log_file" >&2 || true
  kill "$pid" 2>/dev/null || true
  exit 1
fi

if [ "$ephemeral" = "1" ]; then
  windows_pid=$(windows_listener_pid || true)
fi

run_validations
if [ "$ephemeral" = "1" ]; then
  cleanup_started_model
  trap - EXIT INT TERM
  echo "lai-gateway-model: stopped ephemeral server"
fi
