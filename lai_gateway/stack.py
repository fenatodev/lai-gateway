from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .config import GatewayConfig, read_control_token
from .daily_config import read_daily_config
from .harness_client import HarnessClient

DEFAULT_HARNESS_REPO = Path("~/dev/projects/lai-local-agent").expanduser()
DEFAULT_LOG_DIR = Path("~/.local/state/lai-gateway").expanduser()
MAX_PROBE_BYTES = 1024 * 1024


def resolve_harness_repo(raw: str | None = None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    env_repo = os.environ.get("LAI_HARNESS_REPO_DIR")
    if env_repo:
        return Path(env_repo).expanduser().resolve()
    sibling = Path(__file__).resolve().parents[2] / "lai-local-agent"
    if sibling.exists():
        return sibling.resolve()
    return DEFAULT_HARNESS_REPO.resolve()


def collect_local_stack_status(
    config: GatewayConfig,
    *,
    harness_repo: Path | None = None,
    gateway_port: int | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    repo = harness_repo or resolve_harness_repo()
    port = gateway_port or config.port
    logs = log_dir or DEFAULT_LOG_DIR
    harness = _probe_harness(config)
    gateway = _probe_gateway(config.bind, port, timeout_seconds=config.timeout_seconds)
    return {
        "product": "lai-gateway-stack",
        "schema_version": 1,
        "overall": "ready" if harness["ready"] and gateway["ready"] else "needs_start",
        "harness_repo": str(repo),
        "log_dir": str(logs.expanduser()),
        "harness": harness,
        "gateway": gateway,
        "model_start_command_available": _command_exists("lai-server-start"),
        "urls": {
            "harness": config.harness_url,
            "gateway": _gateway_url(config.bind, port),
        },
        "security": {
            "tokens_printed": False,
            "private_bind_enabled": config.private_bind_enabled,
            "starts_only_loopback_gateway": config.bind in {"127.0.0.1", "localhost", "::1"},
            "no_browser_open_without_flag": True,
        },
    }


def start_local_stack(
    config: GatewayConfig,
    *,
    harness_repo: Path | None = None,
    gateway_port: int | None = None,
    log_dir: Path | None = None,
    start_model: bool = True,
    open_browser: bool = False,
    check_only: bool = False,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    repo = harness_repo or resolve_harness_repo()
    port = gateway_port or config.port
    logs = (log_dir or DEFAULT_LOG_DIR).expanduser()
    payload = collect_local_stack_status(config, harness_repo=repo, gateway_port=port, log_dir=logs)
    payload["actions"] = []
    payload["check_only"] = bool(check_only)
    if check_only:
        payload["overall"] = "planned" if payload["overall"] != "ready" else "ready"
        payload["planned_commands"] = _planned_commands(config, repo, port)
        return payload

    logs.mkdir(parents=True, exist_ok=True)
    if start_model:
        payload["actions"].append(_run_model_start(repo))
    else:
        payload["actions"].append({"name": "model", "status": "skipped", "reason": "--skip-model"})

    harness = _probe_harness(config)
    if not harness["ready"]:
        payload["actions"].append(_start_harness(config, repo, logs))
        harness = _wait_for(lambda: _probe_harness(config), timeout_seconds=timeout_seconds)
    else:
        payload["actions"].append({"name": "harness", "status": "already_running", "url": config.harness_url})

    gateway = _probe_gateway(config.bind, port, timeout_seconds=config.timeout_seconds)
    if not gateway["ready"]:
        payload["actions"].append(_start_gateway(config, port, logs))
        gateway = _wait_for(lambda: _probe_gateway(config.bind, port, timeout_seconds=config.timeout_seconds), timeout_seconds=timeout_seconds)
    else:
        payload["actions"].append({"name": "gateway", "status": "already_running", "url": _gateway_url(config.bind, port)})

    payload["harness"] = harness
    payload["gateway"] = gateway
    payload["overall"] = "ready" if harness["ready"] and gateway["ready"] else "blocked"
    if open_browser and payload["overall"] == "ready":
        opened = bool(webbrowser.open(payload["urls"]["gateway"], new=2))
        payload["actions"].append({"name": "open_browser", "status": "opened" if opened else "not_opened"})
    return payload


def render_local_stack(payload: dict[str, Any]) -> str:
    lines = [f"lai-gateway stack-start: {payload.get('overall', 'unknown')}"]
    lines.append(f"harness: {payload.get('urls', {}).get('harness', '')}")
    lines.append(f"gateway: {payload.get('urls', {}).get('gateway', '')}")
    lines.append(f"harness_repo: {payload.get('harness_repo', '')}")
    lines.append(f"log_dir: {payload.get('log_dir', '')}")
    for service in ("harness", "gateway"):
        info = payload.get(service, {})
        if isinstance(info, dict):
            status = "ready" if info.get("ready") else "not_ready"
            detail = info.get("detail") or info.get("error") or ""
            lines.append(f"{service}: {status} {detail}".rstrip())
    for action in payload.get("actions", []):
        if not isinstance(action, dict):
            continue
        name = action.get("name", "action")
        status = action.get("status", "unknown")
        detail = action.get("url") or action.get("log") or action.get("reason") or ""
        lines.append(f"action: {name} {status} {detail}".rstrip())
    if payload.get("check_only"):
        for command in payload.get("planned_commands", []):
            lines.append(f"would_run: {command}")
    security = payload.get("security", {})
    if isinstance(security, dict):
        lines.append(f"tokens_printed: {str(security.get('tokens_printed', False)).lower()}")
    return "\n".join(lines)


def _planned_commands(config: GatewayConfig, harness_repo: Path, gateway_port: int) -> list[str]:
    parsed = urlparse(config.harness_url)
    bind = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765
    return [
        "lai-server-start",
        f"cd {harness_repo} && lai serve --bind {bind} --port {port}",
        f"lai-gateway dev --bind {config.bind} --port {gateway_port} --no-open",
    ]


def _probe_harness(config: GatewayConfig) -> dict[str, Any]:
    try:
        client = HarnessClient(config)
        status = client.status()
        readiness = client.readiness()
    except Exception as exc:
        return {"ready": False, "url": config.harness_url, "error": _safe_error(exc)}
    readiness_overall = str(readiness.get("overall") or "unknown")
    capabilities = status.get("capabilities") if isinstance(status.get("capabilities"), dict) else {}
    needs_verified_sandbox = any(
        bool(capabilities.get(name))
        for name in ("async_work_runs", "local_chat_work_runs", "sandbox_workspace_write")
    )
    verified_sandbox_ready = bool(capabilities.get("verified_sandbox_ready"))
    ready = readiness_overall == "ready" and (not needs_verified_sandbox or verified_sandbox_ready)
    result = {
        "ready": ready,
        "url": config.harness_url,
        "product": status.get("product"),
        "version": status.get("version"),
        "repository": status.get("repository"),
        "readiness": readiness_overall,
    }
    if needs_verified_sandbox:
        result["verified_sandbox_ready"] = verified_sandbox_ready
    if not ready:
        if readiness_overall != "ready":
            result["detail"] = f"readiness={readiness_overall}"
        elif needs_verified_sandbox and not verified_sandbox_ready:
            result["detail"] = "verified_sandbox_ready=false"
    return result


def _probe_gateway(bind: str, port: int, *, timeout_seconds: float) -> dict[str, Any]:
    url = f"{_gateway_url(bind, port)}healthz"
    request = Request(url, headers={"Accept": "application/json", "Cache-Control": "no-store"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(MAX_PROBE_BYTES + 1)
            code = response.status
    except HTTPError as exc:
        return {"ready": False, "url": _gateway_url(bind, port), "status_code": exc.code, "error": "http_error"}
    except URLError as exc:
        return {"ready": False, "url": _gateway_url(bind, port), "error": _safe_error(exc)}
    if len(raw) > MAX_PROBE_BYTES:
        return {"ready": False, "url": _gateway_url(bind, port), "error": "response_too_large"}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {}
    return {
        "ready": code == 200 and bool(payload.get("ok", True)),
        "url": _gateway_url(bind, port),
        "status_code": code,
        "product": payload.get("product"),
        "version": payload.get("version"),
    }


def _run_model_start(harness_repo: Path) -> dict[str, Any]:
    if not _command_exists("lai-server-start"):
        return {"name": "model", "status": "skipped", "reason": "lai-server-start not found"}
    try:
        result = subprocess.run(
            ["lai-server-start"],
            cwd=str(harness_repo) if harness_repo.exists() else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90,
            check=False,
        )
    except Exception as exc:
        return {"name": "model", "status": "failed", "reason": _safe_error(exc)}
    return {
        "name": "model",
        "status": "ready" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "detail": _last_safe_line(result.stdout) or _last_safe_line(result.stderr),
    }


def _start_harness(config: GatewayConfig, harness_repo: Path, log_dir: Path) -> dict[str, Any]:
    if not harness_repo.exists():
        return {"name": "harness", "status": "failed", "reason": f"harness repo not found: {harness_repo}"}
    if not _command_exists("lai"):
        return {"name": "harness", "status": "failed", "reason": "lai command not found"}
    parsed = urlparse(config.harness_url)
    bind = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 8765)
    log_path = log_dir / "lai-harness-serve.log"
    command = ["lai", "serve", "--bind", bind, "--port", port]
    with log_path.open("ab") as handle:
        proc = subprocess.Popen(
            command,
            cwd=str(harness_repo),
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=_harness_start_env(),
        )
    return {"name": "harness", "status": "started", "pid": proc.pid, "url": config.harness_url, "log": str(log_path)}


def _harness_start_env() -> dict[str, str]:
    env = os.environ.copy()
    try:
        daily = read_daily_config()
    except Exception:
        return env
    if daily.sandbox_image and not env.get("LAI_REMOTE_SANDBOX_IMAGE"):
        env["LAI_REMOTE_SANDBOX_IMAGE"] = daily.sandbox_image
    if daily.sandbox_python and not env.get("LAI_REMOTE_SANDBOX_PYTHON"):
        env["LAI_REMOTE_SANDBOX_PYTHON"] = daily.sandbox_python
    return env


def _start_gateway(config: GatewayConfig, port: int, log_dir: Path) -> dict[str, Any]:
    log_path = log_dir / "lai-gateway-dev.log"
    command = [sys.executable, "-m", "lai_gateway", "dev", "--bind", config.bind, "--port", str(port), "--no-open"]
    with log_path.open("ab") as handle:
        proc = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    return {"name": "gateway", "status": "started", "pid": proc.pid, "url": _gateway_url(config.bind, port), "log": str(log_path)}


def _wait_for(probe, *, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = probe()
    while time.monotonic() < deadline:
        if last.get("ready"):
            return last
        time.sleep(1)
        last = probe()
    return last


def _gateway_url(bind: str, port: int) -> str:
    if ":" in bind and not bind.startswith("["):
        return f"http://[{bind}]:{port}/"
    return f"http://{bind}:{port}/"


def _command_exists(name: str) -> bool:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return True
    return False


def _safe_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    try:
        token = read_control_token(GatewayConfig.from_env().token_file)
    except Exception:
        token = ""
    if token:
        text = text.replace(token, "[redacted-token]")
    return text[:240]


def _last_safe_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1][:240]
