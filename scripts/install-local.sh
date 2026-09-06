#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}
bin_dir=${LAI_GATEWAY_INSTALL_BIN:-"$HOME/.local/bin"}
mkdir -p "$bin_dir"

cat > "$bin_dir/lai-gateway" <<EOF
#!/usr/bin/env sh
repo_dir='$repo_dir'
python_bin='$python_bin'
if [ -n "\${PYTHONPATH:-}" ]; then
  export PYTHONPATH="\$repo_dir:\$PYTHONPATH"
else
  export PYTHONPATH="\$repo_dir"
fi
exec "\$python_bin" -m lai_gateway "\$@"
EOF
chmod 755 "$bin_dir/lai-gateway"

cat > "$bin_dir/lai-gateway-ui" <<EOF
#!/usr/bin/env sh
repo_dir='$repo_dir'
exec "\$repo_dir/scripts/launch-local.sh" "\$@"
EOF
chmod 755 "$bin_dir/lai-gateway-ui"

cat > "$bin_dir/lai-gateway-mobile" <<EOF
#!/usr/bin/env sh
repo_dir='$repo_dir'
exec "\$repo_dir/scripts/launch-mobile.sh" "\$@"
EOF
chmod 755 "$bin_dir/lai-gateway-mobile"

printf 'installed lai-gateway wrappers in %s\n' "$bin_dir"
"$bin_dir/lai-gateway" --version
