#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
daily_config_loaded=0
# Explicit environment must win over persisted defaults. The config loader prints
# token-free shell exports, but those exports are only defaults, not a dictator.
had_mobile_ip=${LAI_GATEWAY_MOBILE_IP+x}; original_mobile_ip=${LAI_GATEWAY_MOBILE_IP:-}
had_mobile_port=${LAI_GATEWAY_MOBILE_PORT+x}; original_mobile_port=${LAI_GATEWAY_MOBILE_PORT:-}
had_proxy_port=${LAI_GATEWAY_MOBILE_PROXY_PORT+x}; original_proxy_port=${LAI_GATEWAY_MOBILE_PROXY_PORT:-}
had_phone_url=${LAI_GATEWAY_PHONE_URL+x}; original_phone_url=${LAI_GATEWAY_PHONE_URL:-}
had_harness_repo=${LAI_HARNESS_REPO_DIR+x}; original_harness_repo=${LAI_HARNESS_REPO_DIR:-}
daily_config_env=""
if [ -n "${LAI_GATEWAY_DAILY_CONFIG:-}" ]; then
  daily_config_env=$("$python_bin" -m lai_gateway daily-config env --path "$LAI_GATEWAY_DAILY_CONFIG" 2>/dev/null || true)
else
  daily_config_env=$("$python_bin" -m lai_gateway daily-config env 2>/dev/null || true)
fi
if [ -n "$daily_config_env" ]; then
  eval "$daily_config_env"
  daily_config_loaded=1
fi
if [ -n "$had_mobile_ip" ]; then export LAI_GATEWAY_MOBILE_IP="$original_mobile_ip"; fi
if [ -n "$had_mobile_port" ]; then export LAI_GATEWAY_MOBILE_PORT="$original_mobile_port"; fi
if [ -n "$had_proxy_port" ]; then export LAI_GATEWAY_MOBILE_PROXY_PORT="$original_proxy_port"; fi
if [ -n "$had_phone_url" ]; then export LAI_GATEWAY_PHONE_URL="$original_phone_url"; fi
if [ -n "$had_harness_repo" ]; then export LAI_HARNESS_REPO_DIR="$original_harness_repo"; fi
candidate_ip=${LAI_GATEWAY_MOBILE_IP:-}
port=${LAI_GATEWAY_MOBILE_PORT:-8787}
proxy_listen_host=${LAI_GATEWAY_MOBILE_PROXY_LISTEN_HOST:-127.0.0.1}
proxy_listen_port=${LAI_GATEWAY_MOBILE_PROXY_PORT:-18787}
harness_repo=${LAI_HARNESS_REPO_DIR:-"$HOME/dev/projects/lai-local-agent"}
log_dir=${LAI_GATEWAY_LOG_DIR:-"$HOME/.local/state/lai-gateway"}
start_model=1
start_harness=1
start_mobile=1
start_proxy=1
telegram_notify=0
show_pair=0
check_only=0

usage() {
  cat <<USAGE
usage: lai-gateway-daily [--candidate-ip <private-ip>] [options]

Start or validate the daily local LAI workflow:
  1. model server through lai-server-start
  2. lai harness control plane
  3. private lai-gateway mobile server
  4. loopback mobile proxy for Tailscale Serve
  5. final ops-status summary

Options:
  --candidate-ip IP       WSL/private IP where mobile gateway binds; defaults to daily-config
  --port PORT             mobile gateway target port, default 8787
  --proxy-port PORT       loopback proxy port, default 18787
  --harness-repo PATH     lai harness repo, default ~/dev/projects/lai-local-agent
  --telegram-notify       request Telegram mobile notification when gateway starts
  --show-pair             print a fresh short-lived pair token once
  --skip-model            do not run lai-server-start
  --skip-harness          do not start/check lai harness control plane
  --skip-mobile           do not start/check mobile gateway
  --skip-proxy            do not start/check mobile proxy
  --check-only            print the planned workflow without starting services
  LAI_GATEWAY_DAILY_CONFIG can point to an alternate daily config file.
  -h, --help              show this help

Token values are never printed unless --show-pair is passed explicitly from an interactive terminal.
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
    --proxy-port)
      proxy_listen_port=${2:?--proxy-port requires a value}
      shift 2
      ;;
    --harness-repo)
      harness_repo=${2:?--harness-repo requires a value}
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
    --skip-model)
      start_model=0
      shift
      ;;
    --skip-harness)
      start_harness=0
      shift
      ;;
    --skip-mobile)
      start_mobile=0
      shift
      ;;
    --skip-proxy)
      start_proxy=0
      shift
      ;;
    --check-only)
      check_only=1
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
  echo "error: --candidate-ip is required, or set LAI_GATEWAY_MOBILE_IP, or run lai-gateway daily-config set" >&2
  exit 2
fi

mkdir -p "$log_dir"

say() { printf '%s\n' "$*"; }
json_get() {
  local key=$1
  JSON_INPUT=${2:-} "$python_bin" - "$key" <<'PY'
import json, os, sys
key = sys.argv[1]
try:
    data = json.loads(os.environ.get("JSON_INPUT", ""))
except json.JSONDecodeError:
    data = {}
cur = data
for part in key.split('.'):
    if not isinstance(cur, dict):
        cur = None
        break
    cur = cur.get(part)
print("" if cur is None else cur)
PY
}

harness_ready() {
  if ! command -v lai >/dev/null 2>&1; then
    return 1
  fi
  if [ -d "$harness_repo" ]; then
    (cd "$harness_repo" && lai readiness --json >/tmp/lai-gateway-daily-readiness.json 2>/dev/null) || return 1
  else
    lai readiness --json >/tmp/lai-gateway-daily-readiness.json 2>/dev/null || return 1
  fi
  local overall
  overall=$("$python_bin" - <<'PY'
import json
try:
    print(json.load(open('/tmp/lai-gateway-daily-readiness.json')).get('overall',''))
except Exception:
    print('')
PY
)
  [ "$overall" = "ready" ]
}

wait_harness() {
  local i
  for i in $(seq 1 30); do
    if harness_ready; then
      return 0
    fi
    sleep 1
  done
  return 1
}

mobile_listener_active() {
  local status_json active
  status_json=$("$python_bin" -m lai_gateway mobile-status --candidate-ip "$candidate_ip" --port "$port" --json 2>/dev/null || true)
  active=$(json_get listener.active "$status_json")
  [ "$active" = "True" ] || [ "$active" = "true" ]
}

wait_mobile() {
  local i
  for i in $(seq 1 20); do
    if mobile_listener_active; then
      return 0
    fi
    sleep 1
  done
  return 1
}


detect_phone_url() {
  if [ -n "${LAI_GATEWAY_PHONE_URL:-}" ]; then
    printf '%s\n' "$LAI_GATEWAY_PHONE_URL"
    return 0
  fi
  local tmp dns
  tmp=$(mktemp)
  if tailscale status --json >"$tmp" 2>/dev/null || tailscale.exe status --json >"$tmp" 2>/dev/null; then
    dns=$("$python_bin" - "$tmp" "$port" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(1)
dns = ((data.get("Self") or {}).get("DNSName") or "").strip().rstrip(".")
if not dns:
    raise SystemExit(1)
print(f"http://{dns}:{sys.argv[2]}/")
PY
    ) || true
    rm -f "$tmp"
    if [ -n "$dns" ]; then
      printf '%s\n' "$dns"
      return 0
    fi
  else
    rm -f "$tmp"
  fi
  return 1
}

proxy_overall() {
  local proxy_json
  proxy_json=$("$python_bin" -m lai_gateway mobile-proxy --check --listen-host "$proxy_listen_host" --listen-port "$proxy_listen_port" --target-host "$candidate_ip" --target-port "$port" --json 2>/dev/null || true)
  json_get overall "$proxy_json"
}

wait_proxy() {
  local i state
  for i in $(seq 1 20); do
    state=$(proxy_overall)
    if [ "$state" = "ready" ]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

say "lai-gateway-daily: starting"
say "version: $("$python_bin" -m lai_gateway --version | awk '{print $2}')"
say "daily_config: $([ "$daily_config_loaded" = "1" ] && printf loaded || printf none)"
say "mobile_target: ${candidate_ip}:${port}"
say "proxy: http://${proxy_listen_host}:${proxy_listen_port}/ -> http://${candidate_ip}:${port}/"
say "tailscale_serve_target: http://${proxy_listen_host}:${proxy_listen_port}"
phone_url=$(detect_phone_url || true)
if [ -n "$phone_url" ]; then
  say "phone_url: $phone_url"
else
  say "phone_url: open this machine's Tailscale Serve hostname on port ${port}"
fi

if [ "$check_only" = "1" ]; then
  say "check_only: true"
  say "would_run: lai-server-start, lai serve, lai-gateway-mobile, lai-gateway-mobile-proxy, ops-status"
  exit 0
fi

cd "$repo_dir"

if [ "$start_model" = "1" ]; then
  if command -v lai-server-start >/dev/null 2>&1; then
    say "step: model"
    if [ -d "$harness_repo" ]; then
      (cd "$harness_repo" && lai-server-start)
    else
      lai-server-start
    fi
  else
    say "step: model skipped, lai-server-start not found"
  fi
fi

if [ "$start_harness" = "1" ]; then
  say "step: harness"
  if ! harness_ready; then
    if ! command -v lai >/dev/null 2>&1; then
      echo "error: lai command not found; cannot start harness" >&2
      exit 1
    fi
    harness_log="$log_dir/lai-harness-serve.log"
    if [ -d "$harness_repo" ]; then
      (cd "$harness_repo" && nohup lai serve >"$harness_log" 2>&1 &)
    else
      nohup lai serve >"$harness_log" 2>&1 &
    fi
    if ! wait_harness; then
      echo "error: harness did not become ready; inspect $harness_log" >&2
      exit 1
    fi
  fi
  say "harness: ready"
fi

if [ "$start_mobile" = "1" ]; then
  say "step: mobile"
  if ! mobile_listener_active; then
    mobile_log="$log_dir/lai-gateway-mobile.log"
    mobile_args=(--candidate-ip "$candidate_ip" --port "$port")
    if [ "$telegram_notify" = "1" ]; then
      mobile_args+=(--telegram-notify)
    fi
    nohup "$repo_dir/scripts/launch-mobile.sh" "${mobile_args[@]}" >"$mobile_log" 2>&1 &
    if ! wait_mobile; then
      echo "error: mobile gateway did not become ready; inspect $mobile_log" >&2
      exit 1
    fi
  fi
  if [ "$show_pair" = "1" ]; then
    "$python_bin" -m lai_gateway mobile-repair --candidate-ip "$candidate_ip" --port "$port" --prepare --show-pair
  else
    "$python_bin" -m lai_gateway mobile-repair --candidate-ip "$candidate_ip" --port "$port" --prepare >/dev/null
  fi
  say "mobile: ready"
fi

if [ "$start_proxy" = "1" ]; then
  say "step: proxy"
  state=$(proxy_overall)
  if [ "$state" = "ready_to_start" ]; then
    proxy_log="$log_dir/lai-gateway-mobile-proxy.log"
    nohup "$repo_dir/scripts/launch-mobile-proxy.sh" --listen-host "$proxy_listen_host" --listen-port "$proxy_listen_port" --target-host "$candidate_ip" --target-port "$port" >"$proxy_log" 2>&1 &
    if ! wait_proxy; then
      echo "error: mobile proxy did not become ready; inspect $proxy_log" >&2
      exit 1
    fi
  elif [ "$state" != "ready" ]; then
    "$python_bin" -m lai_gateway mobile-proxy --check --listen-host "$proxy_listen_host" --listen-port "$proxy_listen_port" --target-host "$candidate_ip" --target-port "$port"
    echo "error: mobile proxy is not ready" >&2
    exit 1
  fi
  "$python_bin" -m lai_gateway mobile-proxy --check --listen-host "$proxy_listen_host" --listen-port "$proxy_listen_port" --target-host "$candidate_ip" --target-port "$port"
fi

say "step: ops"
"$python_bin" -m lai_gateway ops-status --candidate-ip "$candidate_ip" --port "$port"
if [ -n "${phone_url:-}" ]; then
  say "phone_url: $phone_url"
else
  say "phone_url: open this machine's Tailscale Serve hostname on port ${port}"
fi
say "lai-gateway-daily: ready"
