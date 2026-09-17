import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

from .errors import ConfigError

Runner = Callable[..., subprocess.CompletedProcess[str]]
PopenFactory = Callable[..., subprocess.Popen[Any]]

_PROCESS_CAPABILITIES: dict[str, dict[str, object]] = {
    "network_discovery": {
        "executables": {"tailscale", "tailscale.exe", "powershell.exe"},
        "starts_background_process": False,
        "mutates_system": False,
    },
    "windows_bridge": {
        "executables": {"powershell.exe"},
        "starts_background_process": False,
        "mutates_system": True,
    },
    "local_system_probe": {
        "executables": {"ip", "lscpu", "free", "systemctl"},
        "starts_background_process": False,
        "mutates_system": False,
    },
    "local_stack_start": {
        "executables": {"lai", "lai-server-start"},
        "allow_python_executable": True,
        "starts_background_process": True,
        "mutates_system": False,
    },
    "release_git_read": {
        "executables": {"git"},
        "starts_background_process": False,
        "mutates_system": False,
    },
    "local_task_green_executor": {
        "executables": {"git", "python3", "make"},
        "starts_background_process": False,
        "mutates_system": False,
    },
}


def process_mediation_policy() -> dict[str, Any]:
    return {
        name: {
            "executables": sorted(spec.get("executables", set())),
            "allow_python_executable": bool(spec.get("allow_python_executable", False)),
            "starts_background_process": bool(spec.get("starts_background_process", False)),
            "mutates_system": bool(spec.get("mutates_system", False)),
        }
        for name, spec in sorted(_PROCESS_CAPABILITIES.items())
    }


def run_process(
    args: Sequence[str],
    *,
    capability: str,
    runner: Runner | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = subprocess.PIPE,
    stderr: Any = subprocess.PIPE,
    stdin: Any = None,
    text: bool = True,
    timeout: float | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    argv = _validated_argv(args, capability=capability, starts_background_process=False)
    call = runner or subprocess.run
    return call(
        argv,
        cwd=str(cwd) if isinstance(cwd, Path) else cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        text=text,
        timeout=timeout,
        check=check,
    )


def start_background_process(
    args: Sequence[str],
    *,
    capability: str,
    popen_factory: PopenFactory | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = None,
    stderr: Any = None,
    stdin: Any = None,
    start_new_session: bool = False,
) -> subprocess.Popen[Any]:
    argv = _validated_argv(args, capability=capability, starts_background_process=True)
    call = popen_factory or subprocess.Popen
    return call(
        argv,
        cwd=str(cwd) if isinstance(cwd, Path) else cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        start_new_session=start_new_session,
    )


def _validated_argv(args: Sequence[str], *, capability: str, starts_background_process: bool) -> list[str]:
    if isinstance(args, str):
        raise ConfigError("tool mediation requires argv list, not shell command string")
    argv = list(args)
    if not argv or not all(isinstance(item, str) and item for item in argv):
        raise ConfigError("tool mediation requires non-empty string argv")
    spec = _PROCESS_CAPABILITIES.get(capability)
    if spec is None:
        raise ConfigError(f"unknown process capability: {capability}")
    if starts_background_process and not spec.get("starts_background_process"):
        raise ConfigError(f"capability cannot start background process: {capability}")
    executable = _executable_name(argv[0])
    allowed = set(spec.get("executables", set()))
    python_allowed = bool(spec.get("allow_python_executable", False)) and executable.startswith("python")
    if executable not in allowed and not python_allowed:
        raise ConfigError(f"executable not allowed for capability {capability}: {executable}")
    return argv


def _executable_name(raw: str) -> str:
    return Path(raw).name.lower()
