#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"
TARGET_VERSION="${LAI_GATEWAY_DOGFOOD_TARGET:-}"
ALLOW_DIRTY="false"
CHECK_ONLY="false"

usage() {
  cat <<'USAGEEOF'
Usage: scripts/local-clean-dogfood.sh [--allow-dirty] [--check-only]

Runs a bounded local dogfood loop for the source checkout:
  - release-check and alpha-readiness gates
  - Workbench static surface markers
  - local model absent fallback
  - local model present via ephemeral loopback fixture
  - restricted local document text and document workbench

The script does not install packages, start persistent services, use credentials,
open a browser, submit forms, activate n8n, execute MCP tools, publish releases,
or inspect HOME. Temporary files stay under the repository state/ directory.
USAGEEOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-dirty) ALLOW_DIRTY="true" ;;
    --check-only) CHECK_ONLY="true" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"
if [[ -z "$TARGET_VERSION" ]]; then
  TARGET_VERSION="$("$PYTHON_BIN" - <<'VERSIONPY'
from lai_gateway import __version__
print(__version__)
VERSIONPY
)"
fi

tmp_dir=""
model_pid=""
cleanup() {
  if [[ -n "$model_pid" ]]; then
    kill "$model_pid" >/dev/null 2>&1 || true
    wait "$model_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

run_gateway() {
  "$PYTHON_BIN" -m lai_gateway "$@"
}

json_assert() {
  local label="$1"
  local path="$2"
  local code="$3"
  "$PYTHON_BIN" - "$label" "$path" "$code" <<'JSONASSERTPY'
import json
import sys
label, path, code = sys.argv[1], sys.argv[2], sys.argv[3]
payload = json.load(open(path, encoding="utf-8"))
ns = {"payload": payload}
try:
    ok = bool(eval(code, {"__builtins__": {}}, ns))
except Exception as exc:
    print(f"{label}: assertion-error {exc.__class__.__name__}")
    raise SystemExit(1)
if not ok:
    print(f"{label}: assertion-failed")
    raise SystemExit(1)
print(f"{label}: ready")
JSONASSERTPY
}

if [[ "$CHECK_ONLY" == "true" ]]; then
  echo "local-clean-dogfood: plan"
  echo "release gate: release-check/alpha-readiness"
  echo "workbench surface: static markers only"
  echo "model absent: explicit local fallback"
  echo "model present: ephemeral loopback fixture"
  echo "documents: .txt/.md/.json only with blocked PDF check"
  echo "side effects: temp state only; no install, no browser, no n8n, no MCP tool execution, no publication"
  exit 0
fi

echo "local-clean-dogfood: start"

dirty_status="$(git status --short)"
if [[ -n "$dirty_status" && "$ALLOW_DIRTY" != "true" ]]; then
  echo "git status: dirty"
  exit 1
fi
if [[ -n "$dirty_status" ]]; then
  echo "git status: allowed-dirty"
else
  echo "git status: clean"
fi

tmp_dir="$repo_root/state/local-clean-dogfood.$$"
mkdir -p "$tmp_dir/workspace"

echo "version: $(run_gateway --version | sed 's/[[:space:]]\+/ /g')"
set +e
run_gateway release-check --target "$TARGET_VERSION" --json >"$tmp_dir/release.json"
release_rc=$?
set -e
if [[ "$release_rc" -ne 0 && "$ALLOW_DIRTY" != "true" ]]; then
  echo "release gate: failed"
  exit 1
fi
if [[ "$release_rc" -ne 0 ]]; then
  json_assert "release gate" "$tmp_dir/release.json" "payload.get('overall') == 'blocked' and not [c for c in payload.get('checks', []) if c.get('name') != 'git_status' and c.get('status') != 'ok']"
else
  json_assert "release gate" "$tmp_dir/release.json" "payload.get('overall') == 'ready' and payload.get('phase') in {'tagged', 'ready_to_tag', 'ready_for_integration'}"
fi
set +e
run_gateway alpha-readiness --target "$TARGET_VERSION" --json >"$tmp_dir/alpha.json"
alpha_rc=$?
set -e
if [[ "$alpha_rc" -ne 0 && "$ALLOW_DIRTY" != "true" ]]; then
  echo "alpha gate: failed"
  exit 1
fi
if [[ "$alpha_rc" -ne 0 ]]; then
  json_assert "alpha gate" "$tmp_dir/alpha.json" "payload.get('overall') == 'blocked' and payload.get('publication_allowed') is False and not [c for c in payload.get('checks', []) if c.get('name') != 'release_check' and c.get('status') != 'ok']"
else
  json_assert "alpha gate" "$tmp_dir/alpha.json" "payload.get('overall') == 'ready' and payload.get('decision') == 'candidate_go' and payload.get('publication_allowed') is False"
fi

grep -q "send-model-chat" lai_gateway/static/app.js
grep -q "refresh-document-workbench" lai_gateway/static/app.js
grep -q "inspect-document-workbench" lai_gateway/static/app.js
grep -q "Alpha técnico" lai_gateway/static/index.html
echo "workbench surface: ready"

set +e
env -u LAI_GATEWAY_MODEL_BASE_URL -u LAI_GATEWAY_MODEL_NAME -u LAI_GATEWAY_MODEL_API_KEY \
  LAI_GATEWAY_MODEL_CONFIG_FILE="$tmp_dir/missing-model.json" \
  "$PYTHON_BIN" -m lai_gateway model-chat --message "dogfood local missing model" --timeout-seconds 1 --json >"$tmp_dir/model-missing.json"
missing_rc=$?
set -e
if [[ "$missing_rc" -eq 0 ]]; then
  echo "model absent: expected non-zero fallback rc"
  exit 1
fi
json_assert "model absent fallback" "$tmp_dir/model-missing.json" "payload.get('fallback', {}).get('used') is True and payload.get('fallback', {}).get('cloud_fallback') is False and payload.get('conversation', {}).get('creates_harness_run') is False"

"$PYTHON_BIN" - "$tmp_dir/model-port" <<'MODELSERVERPY' &
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return
    def _send(self, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/v1/models":
            self._send({"data": [{"id": "dogfood-local-model"}]})
            return
        self.send_error(404)
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            self._send({"choices": [{"message": {"content": "resposta local dogfood pronta"}}]})
            return
        self.send_error(404)

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
open(sys.argv[1], "w", encoding="utf-8").write(str(server.server_port))
server.serve_forever()
MODELSERVERPY
model_pid=$!
for _ in $(seq 1 50); do
  [[ -s "$tmp_dir/model-port" ]] && break
  sleep 0.1
done
if [[ ! -s "$tmp_dir/model-port" ]]; then
  echo "model fixture: failed"
  exit 1
fi
model_port="$(cat "$tmp_dir/model-port")"
env LAI_GATEWAY_MODEL_CONFIG_FILE="$tmp_dir/no-persisted-config.json" \
  LAI_GATEWAY_MODEL_BASE_URL="http://127.0.0.1:${model_port}" \
  LAI_GATEWAY_MODEL_NAME="dogfood-local-model" \
  "$PYTHON_BIN" -m lai_gateway model-chat --message "dogfood local present model" --timeout-seconds 3 --json >"$tmp_dir/model-present.json"
json_assert "model present loopback" "$tmp_dir/model-present.json" "payload.get('overall') == 'ready' and payload.get('fallback', {}).get('used') is False and payload.get('network_calls', {}).get('local_openai_chat_completion') is True and payload.get('security', {}).get('cloud_fallback') is False and payload.get('security', {}).get('creates_harness_run') is False"

printf 'dogfood document ok\n' >"$tmp_dir/workspace/dogfood.md"
printf '{"dogfood": true}\n' >"$tmp_dir/workspace/context.json"
printf '%s\n' '%PDF-1.7 fake blocked' >"$tmp_dir/workspace/blocked.pdf"
run_gateway document-text-local --workspace-root "$tmp_dir/workspace" --relative-path dogfood.md --max-chars 200 --json >"$tmp_dir/document-ok.json"
json_assert "document text" "$tmp_dir/document-ok.json" "payload.get('overall') == 'ready' and payload.get('security', {}).get('untrusted_content') is True and payload.get('security', {}).get('supports_pdf') is False and payload.get('security', {}).get('filesystem_write') is False"
set +e
run_gateway document-text-local --workspace-root "$tmp_dir/workspace" --relative-path blocked.pdf --json >"$tmp_dir/document-pdf.json"
pdf_rc=$?
set -e
if [[ "$pdf_rc" -eq 0 ]]; then
  echo "document pdf block: expected non-zero rc"
  exit 1
fi
json_assert "document pdf block" "$tmp_dir/document-pdf.json" "payload.get('overall') == 'blocked' and payload.get('security', {}).get('supports_pdf') is False"
"$PYTHON_BIN" - "$tmp_dir/workspace" <<'DOCWORKBENCHPY'
import sys
from pathlib import Path
from lai_gateway.document_workbench import collect_document_workbench
payload = collect_document_workbench(
    workspace_root=Path(sys.argv[1]),
    selected_relative_path="dogfood.md",
    max_results=10,
    max_chars=200,
)
assert payload["overall"] == "ready"
assert payload["limits"]["metadata_only_selection"] is True
assert payload["limits"]["recursive_listing"] is False
assert payload["security"]["external_upload"] is False
assert payload["security"]["grants_permission"] is False
print("document workbench: ready")
DOCWORKBENCHPY

echo "side effects: temp-state-only"
echo "local-clean-dogfood: ready"
