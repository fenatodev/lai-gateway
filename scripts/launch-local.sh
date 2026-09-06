#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
open_browser=${LAI_GATEWAY_OPEN_BROWSER:-1}

args=("$@")
if [ "$open_browser" != "1" ]; then
  args=("--no-open" "${args[@]}")
fi
cd "$repo_dir"
exec "$python_bin" -m lai_gateway dev "${args[@]}"
