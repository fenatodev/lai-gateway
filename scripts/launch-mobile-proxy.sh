#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
cd "$repo_dir"
exec "$python_bin" -m lai_gateway mobile-proxy "$@"
