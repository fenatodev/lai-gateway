#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

usage() {
  cat <<'EOF'
Usage: publication-scan.sh [PATH ...]

Scans public lai-gateway release surfaces for private local paths, known local IPs, and blocked release-prose phrases.
With no paths, scans README, changelog, package metadata, docs, scripts, and
runtime source. Tests and cache directories are intentionally excluded because
they contain synthetic secret fixtures.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "${1:-}" = "help" ]; then
  usage
  exit 0
fi

patterns=(
  '/home/[[:alnum:]_.-]+'
  '/mnt/c/Users/[[:alnum:]_.-]+'
  'C:\\Users\\[[:alnum:]_.-]+'
  '172\.29\.[0-9]{1,3}\.[0-9]{1,3}'
  '100\.107\.179\.6'
  '192\.168\.15\.4'
  'Humanity has made many mistake[s]'
  'Tiny mercy in a world full of tracking pixel[s]'
  'Humanity gets one less obvious wa[y]'
  'Tiny outbreak of restrain[t]'
)
if [ "$#" -gt 0 ]; then
  scan_paths=("$@")
else
  scan_paths=(
    "$repo_dir/README.md"
    "$repo_dir/CHANGELOG.md"
    "$repo_dir/Makefile"
    "$repo_dir/pyproject.toml"
    "$repo_dir/docs"
    "$repo_dir/lai_gateway"
    "$repo_dir/scripts"
  )
fi

matches=0
for pattern in "${patterns[@]}"; do
  if grep -RInE --binary-files=without-match \
    --exclude='*.pyc' \
    --exclude-dir='__pycache__' \
    --exclude-dir='.git' \
    --exclude-dir='.venv' \
    -- "$pattern" "${scan_paths[@]}"; then
    matches=1
  fi
done

if [ "$matches" -ne 0 ]; then
  echo "publication scan failed: private local path, known local IP, or blocked release prose found" >&2
  exit 1
fi

echo "Publication scan passed: no private local paths, known local IPs, or blocked release prose found in public surfaces."
