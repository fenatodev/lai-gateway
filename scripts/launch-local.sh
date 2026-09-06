#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
open_browser=${LAI_GATEWAY_OPEN_BROWSER:-1}
bind=${LAI_GATEWAY_BIND:-127.0.0.1}
port=${LAI_GATEWAY_PORT:-8787}

args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[$i]}" in
    --bind)
      if (( i + 1 < ${#args[@]} )); then bind=${args[$((i + 1))]}; fi
      ;;
    --bind=*)
      bind=${args[$i]#--bind=}
      ;;
    --port)
      if (( i + 1 < ${#args[@]} )); then port=${args[$((i + 1))]}; fi
      ;;
    --port=*)
      port=${args[$i]#--port=}
      ;;
  esac
done

url="http://$bind:$port/"
printf 'lai-gateway UI: %s\n' "$url"
if [ "$open_browser" = "1" ]; then
  (
    sleep 1
    cd "$repo_dir"
    LAI_GATEWAY_BIND="$bind" LAI_GATEWAY_PORT="$port" "$python_bin" -m lai_gateway open-ui >/dev/null 2>&1 || true
  ) &
fi
cd "$repo_dir"
exec "$python_bin" -m lai_gateway serve "$@"
