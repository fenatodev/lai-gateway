from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__

_MODEL_RUNTIME_COMMANDS = (
    "ollama",
    "llama-server",
    "llama-cli",
    "llamafile",
    "docker",
    "podman",
)
_WINDOWS_RUNTIME_COMMANDS = ("ollama.exe", "llama-server.exe", "llama-cli.exe")
_WINDOWS_LLAMA_CPP_DEFAULT_PORT = 18082
_DEFAULT_MODEL_API_KEY_FILE = "~/.config/lai-gateway/model-api-key"
_DEFAULT_MODEL_RUNS_FILE = "~/.local/share/lai-gateway/model-runs.jsonl"
_DEFAULT_MODEL_API_KEY_BYTES = 32
_GPU_COMMANDS = ("rocminfo", "rocm-smi", "clinfo", "nvidia-smi")
_SECRET_ENV_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "AUTH", "BEARER")

_MODEL_FILE_DEFAULT_ROOTS = (
    "~/models",
    "~/.cache/huggingface",
    "/mnt/c/Users/fenat/Downloads",
    "/mnt/c/Users/fenat/Documents",
    "/mnt/c/Users/fenat/.cache/huggingface",
    "/mnt/c/Users/fenat/.lmstudio/models",
    "/mnt/c/Users/fenat/AppData/Local/nomic.ai/GPT4All",
)
_SPLIT_GGUF_RE = re.compile(r"^(?P<stem>.+)-(?P<idx>\d{5})-of-(?P<total>\d{5})\.gguf$", re.IGNORECASE)

_MODEL_TASKS: dict[str, dict[str, Any]] = {
    "code-mini": {
        "title": "minimal Python code generation",
        "prompt": "Return only this exact one-line Python function, with no markdown: def lai_add(a, b): return a + b",
        "max_tokens": 64,
        "temperature": 0,
        "required_markers": ("def lai_add", "return a + b"),
    },
    "json-mini": {
        "title": "minimal structured JSON generation",
        "prompt": 'Return only this exact compact JSON object, with no markdown: {"lai_json_status":"ok","count":2}',
        "max_tokens": 64,
        "temperature": 0,
        "required_markers": ('"lai_json_status"', '"ok"', '"count"', "2"),
    },
}


def collect_model_status(*, env: dict[str, str] | None = None, probe_openai: bool = False) -> dict[str, Any]:
    """Return a read-only local model readiness snapshot.

    The default path intentionally performs no model download, no server startup, and no remote calls.
    """
    values = env if env is not None else os.environ
    commands = {name: _command_payload(name) for name in (*_MODEL_RUNTIME_COMMANDS, *_GPU_COMMANDS, "python3")}
    windows_commands = _windows_runtime_payloads(values)
    hardware = _hardware_snapshot()
    raw_base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    api_key = _model_api_key_from_env(values)
    config = _model_env_config(values)
    openai_probe = _probe_openai_compatible(raw_base_url, api_key=api_key) if probe_openai and raw_base_url else None
    overall = _overall(commands=commands, windows_commands=windows_commands, config=config, openai_probe=openai_probe)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-status",
        "overall": overall,
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "network_calls": {"local_openai_probe": bool(openai_probe and openai_probe.get("network_call"))},
        "commands": commands,
        "windows_commands": windows_commands,
        "hardware": hardware,
        "model_config": config,
        "openai_probe": openai_probe,
        "recommendation": _recommendation(commands=commands, windows_commands=windows_commands, config=config, hardware=hardware, openai_probe=openai_probe),
        "next_steps": _next_steps(commands=commands, windows_commands=windows_commands, config=config, openai_probe=openai_probe),
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "downloads_models": False,
            "redacts_secret_env": True,
            "direct_llama_proxy_exposed_to_mobile": False,
        },
    }


def render_model_status(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway model-status: {payload['overall']}",
        f"version: {payload['version']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
    ]
    config = payload["model_config"]
    lines.append(f"model_base_url_configured: {str(bool(config.get('base_url'))).lower()}")
    lines.append(f"model_name_configured: {str(bool(config.get('model'))).lower()}")
    runtimes = payload["commands"]
    available = [name for name in _MODEL_RUNTIME_COMMANDS if runtimes.get(name, {}).get("available")]
    windows_runtimes = payload.get("windows_commands", {})
    windows_available = [name for name in _WINDOWS_RUNTIME_COMMANDS if windows_runtimes.get(name, {}).get("available")]
    gpu_tools = [name for name in _GPU_COMMANDS if runtimes.get(name, {}).get("available")]
    lines.append(f"runtime_tools: {', '.join(available) if available else 'none'}")
    if windows_runtimes:
        lines.append(f"windows_runtime_tools: {', '.join(windows_available) if windows_available else 'none'}")
    lines.append(f"gpu_tools: {', '.join(gpu_tools) if gpu_tools else 'none'}")
    hw = payload["hardware"]
    if hw.get("cpu_model"):
        lines.append(f"cpu: {hw['cpu_model']}")
    if hw.get("memory_total_gib") is not None:
        lines.append(f"memory_total_gib: {hw['memory_total_gib']}")
    if hw.get("wsl") is not None:
        lines.append(f"wsl: {str(hw['wsl']).lower()}")
    if payload.get("openai_probe") is not None:
        lines.append(f"openai_probe: {payload['openai_probe']['status']}")
    lines.append(f"recommendation: {payload['recommendation']}")
    if payload["next_steps"]:
        lines.append("next_steps:")
        lines.extend(f"  {step}" for step in payload["next_steps"])
    return "\n".join(lines)



def collect_model_plan(
    *,
    backend: str = "auto",
    model_name: str | None = None,
    base_url: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a safe, non-mutating plan for connecting a local model runtime."""
    status = collect_model_status(env=env)
    chosen = _choose_model_backend(backend=backend, status=status)
    resolved_base_url = base_url or _default_base_url_for_backend(chosen)
    resolved_model = model_name or "<local-code-model>"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-plan",
        "overall": _plan_overall(chosen),
        "backend": chosen,
        "requested_backend": backend,
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "current_status": status,
        "plan": _model_plan_steps(backend=chosen, model_name=resolved_model, base_url=resolved_base_url),
        "commands": _model_plan_commands(backend=chosen, model_name=resolved_model, base_url=resolved_base_url),
        "warnings": _model_plan_warnings(backend=chosen, status=status),
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "downloads_models": False,
            "remote_endpoint_allowed": False,
            "direct_llama_proxy_exposed_to_mobile": False,
        },
    }


def render_model_plan(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway model-plan: {payload['overall']}",
        f"version: {payload['version']}",
        f"backend: {payload['backend']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
    ]
    if payload.get("warnings"):
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in payload["warnings"])
    lines.append("plan:")
    for item in payload["plan"]:
        lines.append(f"  {item['step']}. {item['title']}")
        lines.append(f"     {item['detail']}")
    lines.append("commands:")
    for label, command in payload["commands"].items():
        lines.append(f"  {label}:")
        lines.append(f"    {command}")
    return "\n".join(lines)





def collect_model_smoke(
    *,
    env: dict[str, str] | None = None,
    expected: str = "LAI_SMOKE_OK",
    timeout_seconds: float = 60.0,
    record: bool = False,
    runs_file: Path | None = None,
) -> dict[str, Any]:
    """Run a bounded fixed-prompt completion smoke test against a safe local model endpoint."""
    values = env if env is not None else os.environ
    raw_base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    model_name = values.get("LAI_GATEWAY_MODEL_NAME", "").strip()
    api_key = _model_api_key_from_env(values)
    started = time.monotonic()
    smoke = _probe_openai_chat_completion(
        raw_base_url,
        model_name=model_name,
        api_key=api_key,
        expected=expected,
        timeout_seconds=timeout_seconds,
    )
    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    overall = "ready" if smoke.get("matched") else smoke.get("status", "blocked")
    if smoke.get("status") in {"blocked", "needs_config"}:
        overall = smoke["status"]
    payload = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-smoke",
        "overall": overall,
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "network_calls": {"local_openai_chat_completion": bool(smoke.get("network_call"))},
        "model_config": _model_env_config(values),
        "smoke": smoke,
        "elapsed_ms": elapsed_ms,
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "downloads_models": False,
            "fixed_prompt_only": True,
            "user_prompt_supported": False,
        },
    }
    if record:
        payload["record"] = append_model_run(payload, path=runs_file)
    return payload


def render_model_smoke(payload: dict[str, Any]) -> str:
    smoke = payload["smoke"]
    lines = [
        f"lai-gateway model-smoke: {payload['overall']}",
        f"version: {payload['version']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
        "fixed_prompt_only: true",
        f"status: {smoke.get('status')}",
    ]
    if smoke.get("auth_used") is not None:
        lines.append(f"auth_used: {str(bool(smoke.get('auth_used'))).lower()}")
    if smoke.get("matched") is not None:
        lines.append(f"matched: {str(bool(smoke.get('matched'))).lower()}")
    if smoke.get("response_preview"):
        lines.append(f"response_preview: {smoke['response_preview']}")
    if smoke.get("detail"):
        lines.append(f"detail: {smoke['detail']}")
    lines.append(f"elapsed_ms: {payload['elapsed_ms']}")
    if payload.get("record"):
        lines.append(f"record: {payload['record'].get('status')} ({payload['record'].get('path')})")
    return "\n".join(lines)

def collect_model_task(
    *,
    env: dict[str, str] | None = None,
    task: str = "code-mini",
    timeout_seconds: float = 60.0,
    record: bool = False,
    runs_file: Path | None = None,
) -> dict[str, Any]:
    """Run a bounded fixed local model task without accepting arbitrary prompts."""
    values = env if env is not None else os.environ
    raw_base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    model_name = values.get("LAI_GATEWAY_MODEL_NAME", "").strip()
    task_spec = _MODEL_TASKS.get(task)
    started = time.monotonic()
    if task_spec is None:
        result = {"status": "blocked", "network_call": False, "detail": f"unsupported fixed model task: {task}"}
    else:
        result = _run_fixed_chat_completion(
            raw_base_url,
            model_name=model_name,
            api_key=_model_api_key_from_env(values),
            messages=[{"role": "user", "content": task_spec["prompt"]}],
            max_tokens=int(task_spec["max_tokens"]),
            temperature=float(task_spec["temperature"]),
            timeout_seconds=timeout_seconds,
            expected_markers=tuple(task_spec["required_markers"]),
        )
    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    overall = "ready" if result.get("matched") else result.get("status", "blocked")
    if result.get("status") in {"blocked", "needs_config"}:
        overall = result["status"]
    payload = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-task",
        "overall": overall,
        "task": task,
        "task_title": task_spec["title"] if task_spec else None,
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "network_calls": {"local_openai_chat_completion": bool(result.get("network_call"))},
        "model_config": _model_env_config(values),
        "result": result,
        "elapsed_ms": elapsed_ms,
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "downloads_models": False,
            "fixed_task_only": True,
            "user_prompt_supported": False,
        },
    }
    if record:
        payload["record"] = append_model_run(payload, path=runs_file)
    return payload


def render_model_task(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"lai-gateway model-task: {payload['overall']}",
        f"version: {payload['version']}",
        f"task: {payload['task']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
        "fixed_task_only: true",
        f"status: {result.get('status')}",
    ]
    if result.get("auth_used") is not None:
        lines.append(f"auth_used: {str(bool(result.get('auth_used'))).lower()}")
    if result.get("matched") is not None:
        lines.append(f"matched: {str(bool(result.get('matched'))).lower()}")
    if result.get("required_markers"):
        lines.append(f"required_markers: {', '.join(result['required_markers'])}")
    if result.get("response_preview"):
        lines.append(f"response_preview: {result['response_preview']}")
    if result.get("detail"):
        lines.append(f"detail: {result['detail']}")
    lines.append(f"elapsed_ms: {payload['elapsed_ms']}")
    if payload.get("record"):
        lines.append(f"record: {payload['record'].get('status')} ({payload['record'].get('path')})")
    return "\n".join(lines)




def collect_model_eval(
    *,
    env: dict[str, str] | None = None,
    tasks: tuple[str, ...] | None = None,
    timeout_seconds: float = 60.0,
    record: bool = False,
    runs_file: Path | None = None,
) -> dict[str, Any]:
    """Run a bounded fixed local model evaluation suite without accepting arbitrary prompts."""
    selected_tasks = tasks or ("code-mini", "json-mini")
    started = time.monotonic()
    smoke = collect_model_smoke(env=env, timeout_seconds=timeout_seconds, record=record, runs_file=runs_file)
    task_results = [
        collect_model_task(env=env, task=task, timeout_seconds=timeout_seconds, record=record, runs_file=runs_file)
        for task in selected_tasks
    ]
    elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    checks = [smoke, *task_results]
    ready_count = sum(1 for item in checks if item.get("overall") == "ready")
    overall = "ready" if ready_count == len(checks) else "warn"
    if any(item.get("overall") == "blocked" for item in checks):
        overall = "blocked"
    if any(item.get("overall") == "needs_config" for item in checks):
        overall = "needs_config"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-eval",
        "overall": overall,
        "starts_server": False,
        "modifies_files": bool(record),
        "downloads_models": False,
        "network_calls": {"local_openai_chat_completion": any(item.get("network_calls", {}).get("local_openai_chat_completion") for item in checks)},
        "record": record,
        "smoke": smoke,
        "tasks": task_results,
        "summary": {
            "checks": len(checks),
            "ready": ready_count,
            "failed": len(checks) - ready_count,
            "task_names": list(selected_tasks),
            "elapsed_ms": elapsed_ms,
        },
        "elapsed_ms": elapsed_ms,
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "downloads_models": False,
            "fixed_prompt_only": True,
            "fixed_task_only": True,
            "user_prompt_supported": False,
            "stores_prompts": False,
            "recording_requires_explicit_flag": True,
        },
    }


def render_model_eval(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"lai-gateway model-eval: {payload['overall']}",
        f"version: {payload['version']}",
        "starts_server: false",
        f"modifies_files: {str(bool(payload.get('modifies_files'))).lower()}",
        "downloads_models: false",
        "fixed_prompt_only: true",
        "fixed_task_only: true",
        f"checks: {summary['checks']}",
        f"ready: {summary['ready']}",
        f"failed: {summary['failed']}",
        f"elapsed_ms: {payload['elapsed_ms']}",
        f"smoke: {payload['smoke'].get('overall')}",
    ]
    for task in payload.get("tasks", []):
        result = task.get("result", {})
        lines.append(f"task {task.get('task')}: {task.get('overall')} matched={str(bool(result.get('matched'))).lower()} elapsed_ms={task.get('elapsed_ms')}")
    if payload.get("record"):
        lines.append("record: enabled")
    return "\n".join(lines)

def default_model_runs_path() -> Path:
    return Path(os.environ.get("LAI_GATEWAY_MODEL_RUNS_FILE", _DEFAULT_MODEL_RUNS_FILE)).expanduser()


def append_model_run(payload: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    target = (path or default_model_runs_path()).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = _model_run_record(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(target), flags, 0o600)
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    finally:
        if not os.path.exists(target):
            return {"status": "error", "path": str(target), "detail": "record file was not created"}
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return {"status": "written", "path": str(target), "recorded_fields": sorted(record)}


def collect_model_runs(*, path: Path | None = None, limit: int = 20) -> dict[str, Any]:
    target = (path or default_model_runs_path()).expanduser()
    entries = _read_model_run_records(target, limit=limit)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-runs",
        "overall": "ready" if target.exists() else "empty",
        "path": str(target),
        "limit": limit,
        "entries": entries,
        "count": len(entries),
        "summary": _model_run_summary(entries),
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "security": {
            "prints_tokens": False,
            "stores_prompts": False,
            "stores_full_responses": False,
            "stores_response_preview": True,
            "secret_values_recorded": False,
        },
    }


def render_model_runs(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway model-runs: {payload['overall']}",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
        f"count: {payload['count']}",
    ]
    summary = payload.get("summary", {})
    if summary:
        lines.append("summary:")
        lines.append(f"  ready: {summary.get('ready', 0)}")
        lines.append(f"  failed: {summary.get('failed', 0)}")
        if summary.get("avg_elapsed_ms") is not None:
            lines.append(f"  avg_elapsed_ms: {summary['avg_elapsed_ms']}")
    if payload.get("entries"):
        lines.append("entries:")
        for item in payload["entries"]:
            parts = [item.get("created_at", ""), item.get("operation", ""), item.get("overall", "")]
            if item.get("task"):
                parts.append(item["task"])
            if item.get("elapsed_ms") is not None:
                parts.append(f"{item['elapsed_ms']}ms")
            lines.append("  - " + " | ".join(str(part) for part in parts if part))
    return "\n".join(lines)


def _model_run_record(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") or payload.get("smoke") or {}
    config = payload.get("model_config") or {}
    record = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "product": payload.get("product", "lai-gateway"),
        "version": payload.get("version"),
        "operation": payload.get("operation"),
        "overall": payload.get("overall"),
        "task": payload.get("task"),
        "model": config.get("model"),
        "base_url": _redact_url(config.get("base_url") or "") if config.get("base_url") else "",
        "status": result.get("status"),
        "matched": bool(result.get("matched")) if result.get("matched") is not None else None,
        "auth_used": bool(result.get("auth_used")) if result.get("auth_used") is not None else None,
        "elapsed_ms": payload.get("elapsed_ms"),
        "response_chars": result.get("response_chars"),
        "response_preview": (result.get("response_preview") or "")[:200],
    }
    return {k: v for k, v in record.items() if v is not None}


def _read_model_run_records(path: Path, *, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows[-max(1, min(int(limit), 200)):]


def _model_run_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {}
    elapsed = [float(item["elapsed_ms"]) for item in entries if isinstance(item.get("elapsed_ms"), (int, float))]
    ready = sum(1 for item in entries if item.get("overall") == "ready")
    return {
        "ready": ready,
        "failed": len(entries) - ready,
        "operations": sorted({str(item.get("operation")) for item in entries if item.get("operation")}),
        "tasks": sorted({str(item.get("task")) for item in entries if item.get("task")}),
        "avg_elapsed_ms": round(sum(elapsed) / len(elapsed), 1) if elapsed else None,
    }


def default_model_api_key_path() -> Path:
    return Path(_DEFAULT_MODEL_API_KEY_FILE).expanduser()


def create_model_api_key_file(path: Path | None = None, *, force: bool = False, include_key: bool = False) -> dict[str, Any]:
    target = (path or default_model_api_key_path()).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() and not force:
        from .errors import ConfigError

        raise ConfigError(f"model API key file already exists: {target}")
    key = secrets.token_urlsafe(_DEFAULT_MODEL_API_KEY_BYTES)
    _write_model_secret_file(target, key + "\n", force=force)
    payload: dict[str, Any] = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-key-create",
        "path": str(target),
        "created": True,
        "mode": _model_secret_file_mode(target),
        "key_length": len(key),
        "key_printed": include_key,
    }
    if include_key:
        payload["key"] = key
    return payload


def check_model_api_key_file(path: Path | None = None) -> dict[str, Any]:
    target = (path or default_model_api_key_path()).expanduser()
    key = _read_model_api_key_file(target)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-key-check",
        "path": str(target),
        "ok": True,
        "mode": _model_secret_file_mode(target),
        "key_length": len(key),
        "key_printed": False,
    }


def render_model_key(payload: dict[str, Any]) -> str:
    label = payload["operation"]
    lines = [
        f"lai-gateway {label}: ok",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"mode: {payload['mode']}",
        f"key_length: {payload['key_length']}",
        f"key_printed: {str(payload.get('key_printed', False)).lower()}",
    ]
    if payload.get("key_printed") and payload.get("key"):
        lines.append(f"key: {payload['key']}")
    return "\n".join(lines)


def _model_api_key_from_env(values: dict[str, str]) -> str:
    direct = values.get("LAI_GATEWAY_MODEL_API_KEY", "").strip()
    if direct:
        return direct
    file_name = values.get("LAI_GATEWAY_MODEL_API_KEY_FILE", "").strip()
    if not file_name:
        return ""
    try:
        return _read_model_api_key_file(Path(file_name).expanduser())
    except Exception:
        return ""


def _read_model_api_key_file(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        from .errors import ConfigError

        raise ConfigError(f"model API key file not found: {path}") from exc
    except OSError as exc:
        from .errors import ConfigError

        raise ConfigError(f"cannot read model API key file: {path}: {exc}") from exc
    key = raw.strip()
    if not key:
        from .errors import ConfigError

        raise ConfigError(f"model API key file is empty: {path}")
    if any(ch.isspace() for ch in key):
        from .errors import ConfigError

        raise ConfigError("model API key must be a single token without whitespace")
    if len(key) < 32:
        from .errors import ConfigError

        raise ConfigError("model API key must be at least 32 characters")
    _require_model_secret_file_mode(path)
    return key


def _write_model_secret_file(target: Path, content: str, *, force: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT
    if force:
        flags |= os.O_TRUNC
    else:
        flags |= os.O_EXCL
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    os.chmod(target, 0o600)


def _model_secret_file_mode(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    return f"{mode:04o}"


def _require_model_secret_file_mode(path: Path) -> None:
    current_mode = stat.S_IMODE(path.stat().st_mode)
    if os.name == "posix" and not str(path).startswith("/mnt/") and current_mode & 0o077:
        from .errors import ConfigError

        raise ConfigError(f"model API key file permissions must be 0600, got {current_mode:04o}: {path}")

def collect_model_files(
    *,
    paths: list[str] | None = None,
    env: dict[str, str] | None = None,
    max_results: int = 20,
    max_seconds: float = 20.0,
) -> dict[str, Any]:
    """Return a bounded, read-only inventory of local GGUF model files."""
    values = env if env is not None else os.environ
    roots = _model_file_roots(paths=paths, values=values)
    started = time.monotonic()
    file_payloads: list[dict[str, Any]] = []
    truncated = False
    for root in roots:
        if time.monotonic() - started > max_seconds:
            truncated = True
            break
        try:
            matches = root.rglob("*.gguf")
        except OSError:
            continue
        for path in matches:
            if time.monotonic() - started > max_seconds:
                truncated = True
                break
            payload = _gguf_file_payload(path)
            if payload is None:
                continue
            file_payloads.append(payload)
            if len(file_payloads) >= max(100, max_results * 8):
                truncated = True
                break
        if truncated:
            break
    models = _group_gguf_models(file_payloads)
    models.sort(key=_model_sort_key)
    limited = models[:max_results]
    recommended = _recommend_model_file(models)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-files",
        "overall": "ready" if limited else "empty",
        "starts_server": False,
        "modifies_files": False,
        "downloads_models": False,
        "network_calls": False,
        "roots": [str(root) for root in roots],
        "models_found": len(models),
        "models": limited,
        "recommended": recommended,
        "truncated": truncated,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "downloads_models": False,
            "network_calls": False,
        },
    }


def render_model_files(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway model-files: {payload['overall']}",
        f"version: {payload['version']}",
        "starts_server: false",
        "modifies_files: false",
        "downloads_models: false",
        f"models_found: {payload['models_found']}",
    ]
    if payload.get("truncated"):
        lines.append("truncated: true")
    recommended = payload.get("recommended")
    if recommended:
        lines.append("recommended:")
        lines.append(f"  name: {recommended['name']}")
        lines.append(f"  size_total_gib: {recommended['size_total_gib']}")
        lines.append(f"  primary_path: {recommended['primary_path']}")
        if recommended.get("windows_path"):
            lines.append(f"  windows_path: {recommended['windows_path']}")
        for key in ("create_api_key_file", "start_runtime_example", "configure_base_url", "configure_model", "configure_api_key_file", "verify"):
            if recommended.get(key):
                lines.append(f"  {key}: {recommended[key]}")
    if payload.get("models"):
        lines.append("models:")
        for model in payload["models"]:
            flags = []
            if model.get("is_code_model"):
                flags.append("code")
            if model.get("is_split"):
                flags.append(f"split:{model['shard_count']}/{model['shard_total']}")
            if model.get("too_large_for_8gb_target"):
                flags.append(">8GiB")
            if model.get("is_accessory"):
                flags.append("accessory")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"  - {model['name']} [{model['size_total_gib']} GiB]{suffix}")
            lines.append(f"    primary_path: {model['primary_path']}")
    else:
        lines.append("models: none")
    return "\n".join(lines)


def _model_file_roots(*, paths: list[str] | None, values: dict[str, str]) -> list[Path]:
    if paths is not None:
        raw_roots = paths
    elif values.get("LAI_GATEWAY_MODEL_PATHS"):
        raw_roots = list(values.get("LAI_GATEWAY_MODEL_PATHS", "").split(os.pathsep))
    else:
        raw_roots = list(_MODEL_FILE_DEFAULT_ROOTS)
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in raw_roots:
        if not raw:
            continue
        path = Path(raw).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved)
        if key in seen or not path.exists() or not path.is_dir():
            continue
        seen.add(key)
        roots.append(path)
    return roots


def _gguf_file_payload(path: Path) -> dict[str, Any] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    split = _split_gguf(path.name)
    lower = str(path).lower()
    return {
        "name": path.name,
        "path": str(path),
        "windows_path": _to_windows_path(path),
        "size_bytes": stat.st_size,
        "size_gib": round(stat.st_size / (1024 ** 3), 2),
        "split_stem": split["stem"] if split else None,
        "shard_index": split["idx"] if split else None,
        "shard_total": split["total"] if split else None,
        "is_accessory": "mmproj" in lower,
        "is_code_model": any(part in lower for part in ("coder", "code", "deepseek-coder", "starcoder")),
    }


def _split_gguf(name: str) -> dict[str, Any] | None:
    match = _SPLIT_GGUF_RE.match(name)
    if not match:
        return None
    return {
        "stem": match.group("stem"),
        "idx": int(match.group("idx")),
        "total": int(match.group("total")),
    }


def _group_gguf_models(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int | None], list[dict[str, Any]]] = {}
    for item in files:
        parent = str(Path(item["path"]).parent)
        if item.get("split_stem"):
            key = (parent, item["split_stem"], item.get("shard_total"))
        else:
            key = (parent, item["name"].removesuffix(".gguf"), None)
        groups.setdefault(key, []).append(item)
    models: list[dict[str, Any]] = []
    for (_parent, name, split_total), group in groups.items():
        group.sort(key=lambda item: item.get("shard_index") or 0)
        primary = next((item for item in group if item.get("shard_index") in (None, 1)), group[0])
        shard_count = len(group)
        shard_total = int(split_total or shard_count)
        total_size = sum(int(item["size_bytes"]) for item in group)
        is_accessory = all(item.get("is_accessory") for item in group)
        is_code_model = any(item.get("is_code_model") for item in group)
        models.append({
            "name": name,
            "primary_path": primary["path"],
            "windows_path": primary.get("windows_path"),
            "size_total_bytes": total_size,
            "size_total_gib": round(total_size / (1024 ** 3), 2),
            "is_split": split_total is not None,
            "shard_count": shard_count,
            "shard_total": shard_total,
            "complete": shard_count >= shard_total,
            "is_accessory": is_accessory,
            "is_code_model": is_code_model,
            "too_large_for_8gb_target": total_size > 8 * (1024 ** 3),
            "files": group,
        })
    return models


def _model_sort_key(model: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        0 if model.get("is_code_model") else 1,
        0 if model.get("complete") else 1,
        0 if not model.get("is_accessory") else 1,
        0 if not model.get("too_large_for_8gb_target") else 1,
    )



def _wsl_model_api_key_path(windows_model_path: str) -> str:
    prefix = "C:\\Users\\"
    if windows_model_path.startswith(prefix):
        user = windows_model_path[len(prefix):].split("\\", 1)[0]
        return f"/mnt/c/Users/{user}/.config/lai-gateway/model-api-key"
    return str(default_model_api_key_path())


def _windows_model_api_key_path(windows_model_path: str) -> str:
    prefix = "C:\\Users\\"
    if windows_model_path.startswith(prefix):
        user = windows_model_path[len(prefix):].split("\\", 1)[0]
        return f"C:\\Users\\{user}\\.config\\lai-gateway\\model-api-key"
    return "C:\\Users\\<user>\\.config\\lai-gateway\\model-api-key"

def _recommend_model_file(models: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        model for model in models
        if model.get("complete") and not model.get("is_accessory") and not model.get("too_large_for_8gb_target")
    ]
    code = [model for model in candidates if model.get("is_code_model")]
    pool = code or candidates
    if not pool:
        return None
    chosen = sorted(pool, key=lambda model: model["size_total_bytes"], reverse=True)[0]
    windows_path = chosen.get("windows_path") or chosen["primary_path"]
    host = _windows_model_host()
    port = _WINDOWS_LLAMA_CPP_DEFAULT_PORT
    return {
        "name": chosen["name"],
        "primary_path": chosen["primary_path"],
        "windows_path": chosen.get("windows_path"),
        "size_total_gib": chosen["size_total_gib"],
        "is_code_model": chosen["is_code_model"],
        "is_split": chosen["is_split"],
        "create_api_key_file": f"lai-gateway model-key-create --path '{_wsl_model_api_key_path(windows_path)}' --force",
        "start_runtime_example": f"llama-server.exe --host {host} --port {port} --model '{windows_path}' --ctx-size 2048 --threads 8 --n-gpu-layers 0 --api-key-file '{_windows_model_api_key_path(windows_path)}' --cors-origins localhost --no-cors-credentials",
        "configure_base_url": f"export LAI_GATEWAY_MODEL_BASE_URL='http://{host}:{port}'",
        "configure_model": f"export LAI_GATEWAY_MODEL_NAME='{chosen['name']}'",
        "configure_api_key_file": f"export LAI_GATEWAY_MODEL_API_KEY_FILE='{_wsl_model_api_key_path(windows_path)}'",
        "verify": "lai-gateway model-status --probe-openai",
    }


def _to_windows_path(path: Path) -> str | None:
    text = str(path)
    if not text.startswith("/mnt/") or len(text) < 7 or text[6] != "/":
        return None
    drive = text[5].upper()
    rest = text[7:].replace("/", "\\")
    return f"{drive}:\\{rest}"

def _command_payload(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": bool(path), "path": path or None}


def _windows_runtime_payloads(values: dict[str, str]) -> dict[str, Any]:
    if not _is_wsl():
        return {}
    return {name: _windows_command_payload(name, values=values) for name in _WINDOWS_RUNTIME_COMMANDS}


def _windows_command_payload(name: str, *, values: dict[str, str]) -> dict[str, Any]:
    path = shutil.which(name)
    if path:
        return {"available": True, "path": path, "source": "path"}
    for entry in values.get("PATH", "").split(os.pathsep):
        if not entry.startswith("/mnt/"):
            continue
        candidate = Path(entry) / name
        try:
            if candidate.exists():
                return {"available": True, "path": str(candidate), "source": "windows_path"}
        except OSError:
            continue
    return {"available": False, "path": None, "source": None}


def _has_native_inference_runtime(commands: dict[str, Any]) -> bool:
    return any(commands.get(name, {}).get("available") for name in ("ollama", "llama-server", "llama-cli", "llamafile"))


def _has_windows_inference_runtime(windows_commands: dict[str, Any]) -> bool:
    return any(windows_commands.get(name, {}).get("available") for name in _WINDOWS_RUNTIME_COMMANDS)


def _has_windows_llama_cpp(windows_commands: dict[str, Any]) -> bool:
    return any(windows_commands.get(name, {}).get("available") for name in ("llama-server.exe", "llama-cli.exe"))



def _wsl_default_gateway() -> str | None:
    if not _is_wsl():
        return None
    try:
        result = subprocess.run(["ip", "route"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=2)
    except OSError:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
            return parts[2]
    return None


def _windows_model_host() -> str:
    return _wsl_default_gateway() or "<windows-wsl-host-ip>"


def _base_url_host_port(base_url: str, *, default_host: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(base_url)
    return parsed.hostname or default_host, parsed.port or default_port

def _hardware_snapshot() -> dict[str, Any]:
    return {
        "cpu_model": _first_lscpu_value("Model name"),
        "cpu_count": os.cpu_count(),
        "memory_total_gib": _memory_total_gib(),
        "wsl": _is_wsl(),
        "wsl_default_gateway": _wsl_default_gateway(),
        "dev_dxg_present": Path("/dev/dxg").exists(),
        "gpu_note": _gpu_note(),
    }


def _model_env_config(values: dict[str, str]) -> dict[str, Any]:
    base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    model = values.get("LAI_GATEWAY_MODEL_NAME", "").strip()
    provider = values.get("LAI_GATEWAY_MODEL_PROVIDER", "").strip()
    exposed = sorted(_redacted_model_env(values))
    api_key_file = values.get("LAI_GATEWAY_MODEL_API_KEY_FILE", "").strip()
    return {
        "provider": provider or None,
        "base_url": _redact_url(base_url) if base_url else None,
        "model": model or None,
        "configured": bool(base_url or model or provider or values.get("LAI_GATEWAY_MODEL_API_KEY") or api_key_file),
        "api_key_configured": bool(values.get("LAI_GATEWAY_MODEL_API_KEY") or api_key_file),
        "api_key_file": str(Path(api_key_file).expanduser()) if api_key_file else None,
        "env_keys_present": exposed,
    }


def _redacted_model_env(values: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for key in values:
        if not key.startswith("LAI_GATEWAY_MODEL_"):
            continue
        if any(part in key.upper() for part in _SECRET_ENV_PARTS):
            keys.append(f"{key}=<redacted>")
        else:
            keys.append(key)
    return keys


def _redact_url(url: str) -> str:
    if "@" not in url:
        return url
    scheme, rest = url.split("://", 1) if "://" in url else ("", url)
    host = rest.rsplit("@", 1)[-1]
    return f"{scheme}://<redacted>@{host}" if scheme else f"<redacted>@{host}"


class LocalModelClient:
    """Tiny OpenAI-compatible client constrained to safe local/private endpoints."""

    def __init__(self, base_url: str | None, *, model_name: str = "", api_key: str = "", timeout_seconds: float = 60.0) -> None:
        self.raw_base_url = base_url or ""
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.validation = _validate_local_model_base_url(self.raw_base_url) if self.raw_base_url else {
            "status": "blocked",
            "detail": "model base URL is not configured",
        }

    @property
    def auth_used(self) -> bool:
        return bool(self.api_key)

    def readiness_error(self, *, require_model: bool = False) -> dict[str, Any] | None:
        if not self.raw_base_url:
            return {"status": "needs_config", "network_call": False, "detail": "model base URL is not configured"}
        if require_model and not self.model_name:
            return {"status": "needs_config", "network_call": False, "detail": "model name is not configured"}
        if self.validation["status"] != "ok":
            return {"status": "blocked", "network_call": False, "detail": self.validation["detail"]}
        return None

    def get_models(self) -> dict[str, Any]:
        return self._request_json("/v1/models", method="GET", timeout_seconds=min(2.0, self.timeout_seconds))

    def chat_completion(self, *, messages: list[dict[str, str]], max_tokens: int, temperature: float) -> dict[str, Any]:
        body = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        return self._request_json("/v1/chat/completions", method="POST", body=body, timeout_seconds=self.timeout_seconds)

    def _request_json(
        self,
        path: str,
        *,
        method: str,
        body: dict[str, Any] | None = None,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        url = self.validation["base_url"].rstrip("/") + path
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec - validated local/private URL only
                raw = response.read(64 * 1024).decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            return {
                "status": "http_error",
                "network_call": True,
                "auth_used": self.auth_used,
                "code": exc.code,
                "detail": "local model endpoint returned an HTTP error",
            }
        except Exception as exc:  # noqa: BLE001 - diagnostics should be bounded, not crashy
            return {
                "status": "unreachable",
                "network_call": True,
                "auth_used": self.auth_used,
                "detail": str(exc)[:180],
            }
        return {"status": "ready", "network_call": True, "auth_used": self.auth_used, "payload": parsed}


def _probe_openai_compatible(base_url: str | None, *, api_key: str = "") -> dict[str, Any]:
    client = LocalModelClient(base_url, api_key=api_key, timeout_seconds=2.0)
    error = client.readiness_error(require_model=False)
    if error is not None:
        status = "skipped" if error["status"] == "needs_config" else error["status"]
        return {"status": status, "network_call": False, "detail": error["detail"]}
    response = client.get_models()
    if response["status"] != "ready":
        return {key: value for key, value in response.items() if key != "payload"}
    parsed = response.get("payload")
    return {
        "status": "ready",
        "network_call": True,
        "auth_used": client.auth_used,
        "model_count": len(parsed.get("data", [])) if isinstance(parsed, dict) else None,
    }



def _probe_openai_chat_completion(
    base_url: str | None,
    *,
    model_name: str,
    api_key: str = "",
    expected: str = "LAI_SMOKE_OK",
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    expected = (expected or "LAI_SMOKE_OK").strip()[:80] or "LAI_SMOKE_OK"
    return _run_fixed_chat_completion(
        base_url,
        model_name=model_name,
        api_key=api_key,
        messages=[{"role": "user", "content": f"Reply exactly: {expected}"}],
        max_tokens=16,
        temperature=0,
        timeout_seconds=timeout_seconds,
        expected_markers=(expected,),
        expected=expected,
    )


def _run_fixed_chat_completion(
    base_url: str | None,
    *,
    model_name: str,
    api_key: str = "",
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout_seconds: float = 60.0,
    expected_markers: tuple[str, ...] = (),
    expected: str | None = None,
) -> dict[str, Any]:
    client = LocalModelClient(base_url, model_name=model_name, api_key=api_key, timeout_seconds=timeout_seconds)
    error = client.readiness_error(require_model=True)
    if error is not None:
        return error
    response = client.chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature)
    if response["status"] != "ready":
        return {key: value for key, value in response.items() if key != "payload"}
    text = _chat_completion_text(response.get("payload"))
    normalized = _normalize_model_text(text)
    markers = tuple(marker for marker in expected_markers if marker)
    matched = all(_normalize_model_text(marker) in normalized for marker in markers) if markers else bool(text.strip())
    payload: dict[str, Any] = {
        "status": "ready" if matched else "mismatch",
        "network_call": True,
        "auth_used": client.auth_used,
        "matched": matched,
        "response_chars": len(text),
        "response_preview": text.replace("\n", " ")[:200],
    }
    if expected is not None:
        payload["expected"] = expected
    if markers:
        payload["required_markers"] = list(markers)
    return payload


def _chat_completion_text(payload: Any) -> str:
    try:
        choices = payload.get("choices", []) if isinstance(payload, dict) else []
        first = choices[0] if choices else {}
        message = first.get("message", {}) if isinstance(first, dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return content
        text = first.get("text") if isinstance(first, dict) else None
        return text if isinstance(text, str) else ""
    except Exception:
        return ""


def _normalize_model_text(value: str) -> str:
    return " ".join(value.lower().replace("`", "").split())

def _validate_local_model_base_url(base_url: str) -> dict[str, str]:
    parsed = urlparse(base_url)
    if parsed.scheme != "http":
        return {"status": "blocked", "detail": "model probe only allows http:// local endpoints"}
    if parsed.username or parsed.password:
        return {"status": "blocked", "detail": "model base URL must not contain credentials"}
    if parsed.query or parsed.fragment:
        return {"status": "blocked", "detail": "model base URL must not include query or fragment"}
    if not parsed.hostname or not parsed.port:
        return {"status": "blocked", "detail": "model base URL must include host and explicit port"}
    host = parsed.hostname
    allowed = _is_local_probe_host(host)
    if not allowed:
        return {"status": "blocked", "detail": "model probe only allows loopback or private LAN hosts"}
    normalized_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return {"status": "ok", "base_url": f"http://{normalized_host}:{parsed.port}"}


def _is_local_probe_host(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    import ipaddress

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(address.is_loopback or address.is_private)


def _overall(*, commands: dict[str, Any], windows_commands: dict[str, Any], config: dict[str, Any], openai_probe: dict[str, Any] | None) -> str:
    if openai_probe and openai_probe.get("status") == "ready":
        return "ready"
    if openai_probe and openai_probe.get("status") == "blocked":
        return "blocked"
    if config.get("configured"):
        return "warn"
    if _has_native_inference_runtime(commands) or _has_windows_inference_runtime(windows_commands):
        return "needs_model_config"
    if any(commands[name]["available"] for name in ("docker", "podman")):
        return "needs_runtime"
    return "blocked"


def _recommendation(*, commands: dict[str, Any], windows_commands: dict[str, Any], config: dict[str, Any], hardware: dict[str, Any], openai_probe: dict[str, Any] | None) -> str:
    if openai_probe and openai_probe.get("status") == "ready":
        return "local OpenAI-compatible model endpoint is reachable"
    if openai_probe and openai_probe.get("status") == "blocked":
        return "model probe was blocked because the configured endpoint is not a safe local/private HTTP endpoint"
    if config.get("configured"):
        return "model configuration exists, but no live endpoint was confirmed"
    if commands.get("ollama", {}).get("available"):
        return "configure LAI_GATEWAY_MODEL_BASE_URL for the local Ollama/OpenAI-compatible endpoint"
    if _has_windows_llama_cpp(windows_commands):
        return "Windows llama.cpp tools were detected from WSL; start llama-server on Windows, then configure LAI_GATEWAY_MODEL_BASE_URL"
    if windows_commands.get("ollama.exe", {}).get("available"):
        return "Windows Ollama was detected from WSL; expose its local OpenAI-compatible endpoint before probing"
    if commands.get("docker", {}).get("available"):
        if hardware.get("wsl") and not hardware.get("dev_dxg_present"):
            return "Docker is available, but no GPU bridge or inference runtime was detected in WSL; use CPU, Docker, or a Windows-hosted local endpoint"
        return "Docker is available; install or run one local inference backend, then configure LAI_GATEWAY_MODEL_BASE_URL"
    if hardware.get("wsl") and not hardware.get("dev_dxg_present"):
        return "start with a CPU runtime in WSL, or expose a Windows-hosted local model endpoint"
    return "install one local inference runtime before testing a <=8GB code model"


def _next_steps(*, commands: dict[str, Any], windows_commands: dict[str, Any], config: dict[str, Any], openai_probe: dict[str, Any] | None) -> list[str]:
    if openai_probe and openai_probe.get("status") == "ready":
        return ["Run a small read-only harness task against the configured local model backend."]
    if openai_probe and openai_probe.get("status") == "blocked":
        return ["Set LAI_GATEWAY_MODEL_BASE_URL to an http:// loopback or private LAN endpoint with an explicit port before probing."]
    steps: list[str] = []
    if not _has_native_inference_runtime(commands) and not _has_windows_inference_runtime(windows_commands):
        steps.append("Install or expose one inference runtime such as Ollama, llama.cpp, or an OpenAI-compatible local server; Docker alone is only a container path.")
    elif _has_windows_llama_cpp(windows_commands):
        steps.append("Start the detected Windows llama.cpp server with an explicit host/port and a local GGUF model before probing from WSL.")
    if not config.get("base_url"):
        steps.append("Set LAI_GATEWAY_MODEL_BASE_URL to a local OpenAI-compatible endpoint before probing.")
    if not config.get("model"):
        steps.append("Set LAI_GATEWAY_MODEL_NAME after choosing the local code model.")
    steps.append("Do not expose direct llama.cpp or model API proxy routes through the mobile gateway without a separate threat model.")
    return steps



_MODEL_PLAN_BACKENDS = {"auto", "ollama", "llama-cpp", "docker", "windows-openai", "windows-llama-cpp", "windows-ollama"}


def _choose_model_backend(*, backend: str, status: dict[str, Any]) -> str:
    if backend not in _MODEL_PLAN_BACKENDS:
        raise ValueError(f"backend must be one of: {', '.join(sorted(_MODEL_PLAN_BACKENDS))}")
    if backend != "auto":
        return backend
    commands = status.get("commands", {})
    if commands.get("ollama", {}).get("available"):
        return "ollama"
    if commands.get("llama-server", {}).get("available") or commands.get("llama-cli", {}).get("available"):
        return "llama-cpp"
    windows_commands = status.get("windows_commands", {})
    if _has_windows_llama_cpp(windows_commands):
        return "windows-llama-cpp"
    if windows_commands.get("ollama.exe", {}).get("available"):
        return "windows-ollama"
    if commands.get("docker", {}).get("available"):
        return "docker"
    if status.get("hardware", {}).get("wsl"):
        return "windows-openai"
    return "ollama"


def _plan_overall(backend: str) -> str:
    return "ready_to_prepare" if backend in _MODEL_PLAN_BACKENDS else "blocked"


def _default_base_url_for_backend(backend: str) -> str:
    if backend == "ollama":
        return "http://127.0.0.1:11434"
    if backend == "llama-cpp":
        return "http://127.0.0.1:8080"
    if backend == "docker":
        return "http://127.0.0.1:8080"
    if backend == "windows-openai":
        return f"http://{_windows_model_host()}:11434"
    if backend == "windows-llama-cpp":
        return f"http://{_windows_model_host()}:{_WINDOWS_LLAMA_CPP_DEFAULT_PORT}"
    if backend == "windows-ollama":
        return f"http://{_windows_model_host()}:11434"
    return "http://127.0.0.1:11434"


def _model_plan_steps(*, backend: str, model_name: str, base_url: str) -> list[dict[str, str]]:
    if backend == "ollama":
        first = "Install or start Ollama locally, then verify that its local API is listening."
    elif backend == "llama-cpp":
        first = "Install llama.cpp and start llama-server bound to loopback with a local GGUF model."
    elif backend == "docker":
        first = "Run an OpenAI-compatible local inference container bound to 127.0.0.1 only."
    elif backend == "windows-openai":
        first = "Run the model backend on Windows, then expose only a trusted local/private endpoint to WSL."
    elif backend == "windows-llama-cpp":
        first = "Use the detected Windows llama.cpp tools to start llama-server with a local GGUF model and a WSL-reachable host/port."
    elif backend == "windows-ollama":
        first = "Start Windows Ollama and expose only its trusted local/private OpenAI-compatible endpoint to WSL."
    else:
        first = "Pick one local inference runtime before configuring lai-gateway."
    return [
        {"step": "1", "title": "Prepare runtime", "detail": first},
        {"step": "2", "title": "Choose model", "detail": f"Use a local code model that fits RAM/VRAM, then map it as {model_name}."},
        {"step": "3", "title": "Configure gateway", "detail": f"Point lai-gateway at {base_url} and the chosen model name."},
        {"step": "4", "title": "Probe safely", "detail": "Run model-status --probe-openai; it only probes loopback/private HTTP endpoints."},
        {"step": "5", "title": "Keep model behind harness", "detail": "Do not expose raw model or llama.cpp proxy routes to the mobile UI without a separate threat model."},
    ]


def _model_plan_commands(*, backend: str, model_name: str, base_url: str) -> dict[str, str]:
    commands = {
        "configure_base_url": f"export LAI_GATEWAY_MODEL_BASE_URL='{base_url}'",
        "configure_model": f"export LAI_GATEWAY_MODEL_NAME='{model_name}'",
        "verify": "lai-gateway model-status --probe-openai",
        "ops": "lai-gateway ops-status --candidate-ip <private-ip> --port 8787",
    }
    if backend == "ollama":
        commands["runtime_check"] = "ollama --version && curl -fsS http://127.0.0.1:11434/v1/models"
    elif backend == "llama-cpp":
        commands["start_runtime_example"] = "llama-server --host 127.0.0.1 --port 8080 --model /path/to/model.gguf"
    elif backend == "docker":
        commands["runtime_shape"] = "docker run --rm -p 127.0.0.1:8080:8080 <openai-compatible-local-image>"
    elif backend == "windows-openai":
        commands["find_windows_host_from_wsl"] = "ip route | awk '/default via/ {print $3; exit}'"
    elif backend == "windows-llama-cpp":
        host, port = _base_url_host_port(base_url, default_host=_windows_model_host(), default_port=_WINDOWS_LLAMA_CPP_DEFAULT_PORT)
        commands["find_windows_host_from_wsl"] = "ip route | awk '/default via/ {print $3; exit}'"
        commands["create_api_key_file"] = "lai-gateway model-key-create --path '/mnt/c/Users/<user>/.config/lai-gateway/model-api-key' --force"
        commands["start_runtime_example"] = f"llama-server.exe --host {host} --port {port} --model C:\\path\\to\\model.gguf --ctx-size 2048 --threads 8 --n-gpu-layers 0 --api-key-file C:\\Users\\<user>\\.config\\lai-gateway\\model-api-key --cors-origins localhost --no-cors-credentials"
        commands["configure_api_key_file"] = "export LAI_GATEWAY_MODEL_API_KEY_FILE='/mnt/c/Users/<user>/.config/lai-gateway/model-api-key'"
    elif backend == "windows-ollama":
        commands["find_windows_host_from_wsl"] = "ip route | awk '/default via/ {print $3; exit}'"
        commands["runtime_check"] = "curl -fsS http://<windows-host-ip>:11434/v1/models"
    return commands


def _model_plan_warnings(*, backend: str, status: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    hardware = status.get("hardware", {})
    commands = status.get("commands", {})
    if hardware.get("wsl") and not hardware.get("dev_dxg_present"):
        warnings.append("WSL GPU bridge was not detected; expect CPU or Windows-hosted inference unless GPU support is configured outside lai-gateway.")
    if backend == "docker" and not commands.get("docker", {}).get("available"):
        warnings.append("Docker was selected but docker is not available in this environment.")
    if backend == "ollama" and not commands.get("ollama", {}).get("available"):
        warnings.append("Ollama was selected but ollama is not installed in this environment yet.")
    if backend == "llama-cpp" and not (commands.get("llama-server", {}).get("available") or commands.get("llama-cli", {}).get("available")):
        warnings.append("llama.cpp was selected but llama-server/llama-cli is not installed in this environment yet.")
    windows_commands = status.get("windows_commands", {})
    if backend == "windows-llama-cpp" and not _has_windows_llama_cpp(windows_commands):
        warnings.append("Windows llama.cpp was selected but llama-server.exe/llama-cli.exe was not detected from WSL.")
    if backend in {"windows-openai", "windows-llama-cpp", "windows-ollama"}:
        warnings.append("Windows-hosted model endpoints must remain local/private and may require Windows firewall or host-IP configuration for WSL access.")
    warnings.append("This plan intentionally does not download models, install packages, or start servers.")
    return warnings


def _first_lscpu_value(label: str) -> str | None:
    try:
        result = subprocess.run(["lscpu"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=2)
    except OSError:
        return None
    prefix = f"{label}:"
    for line in result.stdout.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _memory_total_gib() -> float | None:
    try:
        result = subprocess.run(["free", "-b"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=2)
    except OSError:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 2:
                return round(int(parts[1]) / (1024 ** 3), 2)
    return None


def _is_wsl() -> bool | None:
    try:
        text = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return None
    return "microsoft" in text or "wsl" in text


def _gpu_note() -> str:
    if Path("/dev/dxg").exists():
        return "WSL GPU bridge device detected"
    if shutil.which("rocm-smi") or shutil.which("nvidia-smi"):
        return "GPU management tool detected"
    return "no GPU runtime tool detected from this environment"
