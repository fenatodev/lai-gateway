from __future__ import annotations

import json
import os
import shutil
import subprocess
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
_GPU_COMMANDS = ("rocminfo", "rocm-smi", "clinfo", "nvidia-smi")
_SECRET_ENV_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "AUTH", "BEARER")


def collect_model_status(*, env: dict[str, str] | None = None, probe_openai: bool = False) -> dict[str, Any]:
    """Return a read-only local model readiness snapshot.

    The default path intentionally performs no model download, no server startup, and no remote calls.
    """
    values = env if env is not None else os.environ
    commands = {name: _command_payload(name) for name in (*_MODEL_RUNTIME_COMMANDS, *_GPU_COMMANDS, "python3")}
    windows_commands = _windows_runtime_payloads(values)
    hardware = _hardware_snapshot()
    raw_base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    config = _model_env_config(values)
    openai_probe = _probe_openai_compatible(raw_base_url) if probe_openai and raw_base_url else None
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


def _hardware_snapshot() -> dict[str, Any]:
    return {
        "cpu_model": _first_lscpu_value("Model name"),
        "cpu_count": os.cpu_count(),
        "memory_total_gib": _memory_total_gib(),
        "wsl": _is_wsl(),
        "dev_dxg_present": Path("/dev/dxg").exists(),
        "gpu_note": _gpu_note(),
    }


def _model_env_config(values: dict[str, str]) -> dict[str, Any]:
    base_url = values.get("LAI_GATEWAY_MODEL_BASE_URL", "").strip()
    model = values.get("LAI_GATEWAY_MODEL_NAME", "").strip()
    provider = values.get("LAI_GATEWAY_MODEL_PROVIDER", "").strip()
    exposed = sorted(_redacted_model_env(values))
    return {
        "provider": provider or None,
        "base_url": _redact_url(base_url) if base_url else None,
        "model": model or None,
        "configured": bool(base_url or model or provider),
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


def _probe_openai_compatible(base_url: str | None) -> dict[str, Any]:
    if not base_url:
        return {"status": "skipped", "network_call": False, "detail": "model base URL is not configured"}
    validation = _validate_local_model_base_url(base_url)
    if validation["status"] != "ok":
        return {"status": "blocked", "network_call": False, "detail": validation["detail"]}
    import urllib.error
    import urllib.request

    url = validation["base_url"].rstrip("/") + "/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:  # nosec - local user-configured URL only
            body = response.read(32 * 1024).decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return {"status": "http_error", "network_call": True, "code": exc.code, "detail": "local model endpoint returned an HTTP error"}
    except Exception as exc:  # noqa: BLE001 - diagnostic should be bounded, not crashy
        return {"status": "unreachable", "network_call": True, "detail": str(exc)[:180]}
    return {"status": "ready", "network_call": True, "model_count": len(parsed.get("data", [])) if isinstance(parsed, dict) else None}


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
        return "http://<windows-host-ip>:11434"
    if backend == "windows-llama-cpp":
        return "http://<windows-host-ip>:8080"
    if backend == "windows-ollama":
        return "http://<windows-host-ip>:11434"
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
        commands["find_windows_host_from_wsl"] = "awk '/nameserver/ {print $2; exit}' /etc/resolv.conf"
    elif backend == "windows-llama-cpp":
        commands["find_windows_host_from_wsl"] = "awk '/nameserver/ {print $2; exit}' /etc/resolv.conf"
        commands["start_runtime_example"] = "llama-server.exe --host <windows-host-ip> --port 8080 --model C:\\path\\to\\model.gguf"
    elif backend == "windows-ollama":
        commands["find_windows_host_from_wsl"] = "awk '/nameserver/ {print $2; exit}' /etc/resolv.conf"
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
