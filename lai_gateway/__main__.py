from __future__ import annotations

import argparse
import getpass
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .bridge import collect_mobile_bridge, render_mobile_bridge
from .access import collect_mobile_access, render_mobile_access
from .config import GatewayConfig
from .contract import summarize_contract
from .doctor import collect_doctor, render_doctor
from .daily_config import collect_daily_config, read_daily_config, render_daily_config, shell_exports, validate_daily_config, write_daily_config
from .errors import GatewayError
from .harness_client import READ_ONLY_RUN_MODES, HarnessClient
from .health import collect_health_report, render_health_report
from .lan import collect_lan_info, render_lan_info
from .model import check_model_api_key_file, collect_model_eval, collect_model_files, collect_model_plan, collect_model_runs, collect_model_smoke, collect_model_status, collect_model_task, create_model_api_key_file, render_model_eval, render_model_files, render_model_key, render_model_plan, render_model_runs, render_model_smoke, render_model_status, render_model_task
from .mobile import (
    collect_mobile_repair,
    collect_mobile_start,
    collect_mobile_status,
    prepare_mobile_serve_config,
    render_mobile_serve_ready,
    render_mobile_repair,
    render_mobile_start,
    render_mobile_status,
)
from .ops import collect_ops_status, render_ops_status
from .proxy import collect_mobile_proxy_status, dump_mobile_proxy_json, render_mobile_proxy_status, run_mobile_proxy, validate_mobile_proxy_config
from .release import collect_release_check, render_release_check
from .server import serve
from .stack import render_local_stack, resolve_harness_repo, start_local_stack
from .service import (
    collect_service_plan,
    install_service_unit,
    remove_service_unit,
    render_service_install,
    render_service_plan,
    render_service_remove,
)
from .telegram import (
    collect_telegram_preflight,
    discover_telegram_chats,
    get_telegram_bot_info,
    inspect_telegram_chat_file,
    inspect_telegram_token_file,
    notify_gateway_status,
    notify_mobile_access,
    render_telegram_bot_info,
    render_telegram_chat_check,
    render_telegram_chat_set,
    render_telegram_discover,
    render_telegram_preflight,
    render_telegram_token_check,
    render_telegram_token_repair,
    render_telegram_token_set,
    repair_telegram_token_whitespace,
    send_telegram_message,
    write_telegram_chat_file,
    write_telegram_token_file,
)
from .tokens import (
    check_gateway_access_token_file,
    check_gateway_pairing_token_file,
    create_gateway_access_token,
    create_gateway_pairing_token,
    default_access_token_path,
    default_pair_token_path,
    revoke_gateway_pairing_token,
)


def _config_with_overrides(config: GatewayConfig, bind: str | None, port: int | None) -> GatewayConfig:
    if bind is None and port is None:
        return config
    values = {
        "LAI_GATEWAY_HARNESS_URL": config.harness_url,
        "LAI_GATEWAY_TOKEN_FILE": str(config.token_file),
        "LAI_GATEWAY_BIND": bind or config.bind,
        "LAI_GATEWAY_PORT": str(port or config.port),
        "LAI_GATEWAY_TIMEOUT_SECONDS": str(config.timeout_seconds),
        "LAI_GATEWAY_PRIVATE_BIND": "1" if config.private_bind_enabled else "0",
    }
    if config.access_token_file is not None:
        values["LAI_GATEWAY_ACCESS_TOKEN_FILE"] = str(config.access_token_file)
    if config.pair_token_file is not None:
        values["LAI_GATEWAY_PAIR_TOKEN_FILE"] = str(config.pair_token_file)
    return GatewayConfig.from_env(values)


def _ui_url(config: GatewayConfig) -> str:
    return f"http://{config.bind}:{config.port}/"


def _run_dev_stack(config: GatewayConfig, *, open_browser: bool) -> int:
    doctor = collect_doctor(config)
    if doctor["overall"] == "blocked":
        print(render_doctor(doctor), file=sys.stderr)
        return 1
    url = _ui_url(config)
    print(f"lai-gateway dev: {doctor['overall']}")
    print(f"harness: {config.harness_url}")
    print(f"access: {config.access_mode}")
    print(f"ui: {url}")
    if open_browser:
        webbrowser.open(url, new=2)
    serve(config)
    return 0



def _release_check_repo() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists():
        return cwd
    return Path(__file__).resolve().parents[1]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lai-gateway")
    parser.add_argument("--version", action="store_true", help="print gateway version and exit")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("config", help="print non-secret gateway configuration")
    sub.add_parser("contract", help="fetch and validate the harness gateway contract")
    sub.add_parser("status", help="fetch harness status through the gateway client")
    sub.add_parser("readiness", help="fetch harness readiness through the gateway client")
    doctor_parser = sub.add_parser("doctor", help="check gateway configuration and harness connectivity")
    doctor_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    ops_parser = sub.add_parser("ops-status", help="show one read-only gateway/mobile/Telegram operations snapshot")
    ops_parser.add_argument("--candidate-ip", default=None, help="private LAN IP to probe for mobile readiness")
    ops_parser.add_argument("--port", type=int, default=None, help="gateway/mobile port to inspect")
    ops_parser.add_argument("--telegram-token-file", default=None, help="telegram bot token file for preflight")
    ops_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for preflight")
    ops_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    health_parser = sub.add_parser("health-report", help="show a compact read-only daily health report")
    health_parser.add_argument("--candidate-ip", default=None, help="private LAN IP to probe for mobile readiness")
    health_parser.add_argument("--port", type=int, default=None, help="gateway/mobile port to inspect")
    health_parser.add_argument("--telegram-token-file", default=None, help="telegram bot token file for preflight or notification")
    health_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for preflight or notification")
    health_parser.add_argument("--telegram-notify", action="store_true", help="send this health report to Telegram when explicitly enabled")
    health_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_parser = sub.add_parser("model-status", help="inspect local model runtime readiness without starting or downloading models")
    model_parser.add_argument("--probe-openai", action="store_true", help="probe the configured local OpenAI-compatible /v1/models endpoint")
    model_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_plan_parser = sub.add_parser("model-plan", help="print a safe non-mutating plan for a local model runtime")
    model_plan_parser.add_argument("--backend", choices=["auto", "ollama", "llama-cpp", "docker", "windows-openai", "windows-llama-cpp", "windows-ollama"], default="auto", help="runtime path to plan")
    model_plan_parser.add_argument("--model-name", default=None, help="local model name to place in exported configuration")
    model_plan_parser.add_argument("--base-url", default=None, help="local OpenAI-compatible base URL to place in exported configuration")
    model_plan_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_files_parser = sub.add_parser("model-files", help="find local GGUF model files without downloads or server startup")
    model_files_parser.add_argument("--path", action="append", default=None, help="directory to scan for GGUF files; repeatable")
    model_files_parser.add_argument("--max-results", type=int, default=20, help="maximum grouped models to print")
    model_files_parser.add_argument("--max-seconds", type=float, default=20.0, help="bounded scan timeout in seconds")
    model_files_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_smoke_parser = sub.add_parser("model-smoke", help="run a fixed-prompt local model completion smoke test")
    model_smoke_parser.add_argument("--expected", default="LAI_SMOKE_OK", help="expected fixed marker for the smoke response")
    model_smoke_parser.add_argument("--timeout-seconds", type=float, default=60.0, help="bounded local completion timeout")
    model_smoke_parser.add_argument("--record", action="store_true", help="append a prompt-free metric record to the local model runs file")
    model_smoke_parser.add_argument("--runs-file", default=None, help="model runs JSONL file path")
    model_smoke_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_task_parser = sub.add_parser("model-task", help="run a fixed local model task without accepting arbitrary prompts")
    model_task_parser.add_argument("--task", choices=["code-mini", "json-mini"], default="code-mini", help="fixed task to run")
    model_task_parser.add_argument("--timeout-seconds", type=float, default=60.0, help="bounded local completion timeout")
    model_task_parser.add_argument("--record", action="store_true", help="append a prompt-free metric record to the local model runs file")
    model_task_parser.add_argument("--runs-file", default=None, help="model runs JSONL file path")
    model_task_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_runs_parser = sub.add_parser("model-runs", help="show prompt-free local model run metrics")
    model_runs_parser.add_argument("--path", default=None, help="model runs JSONL file path")
    model_runs_parser.add_argument("--limit", type=int, default=20, help="maximum recent records to show")
    model_runs_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_eval_parser = sub.add_parser("model-eval", help="run fixed local model smoke and task probes as one suite")
    model_eval_parser.add_argument("--task", action="append", choices=["code-mini", "json-mini"], default=None, help="fixed task to include; repeatable")
    model_eval_parser.add_argument("--timeout-seconds", type=float, default=60.0, help="bounded local completion timeout per check")
    model_eval_parser.add_argument("--record", action="store_true", help="append prompt-free metric records for each check")
    model_eval_parser.add_argument("--runs-file", default=None, help="model runs JSONL file path")
    model_eval_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_key_create_parser = sub.add_parser("model-key-create", help="create a local model API key file without printing the key by default")
    model_key_create_parser.add_argument("--path", default=None, help="model API key file path")
    model_key_create_parser.add_argument("--force", action="store_true", help="overwrite an existing model API key file")
    model_key_create_parser.add_argument("--show-key", action="store_true", help="print the generated key once; avoid using this in shared logs")
    model_key_create_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    model_key_check_parser = sub.add_parser("model-key-check", help="check a local model API key file without printing the key")
    model_key_check_parser.add_argument("--path", default=None, help="model API key file path")
    model_key_check_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    daily_config_parser = sub.add_parser("daily-config", help="store or inspect token-free daily startup defaults")
    daily_config_sub = daily_config_parser.add_subparsers(dest="daily_config_command")
    daily_config_set = daily_config_sub.add_parser("set", help="write token-free daily startup defaults with 0600 permissions")
    daily_config_set.add_argument("--candidate-ip", required=True, help="WSL/private IP where mobile gateway binds")
    daily_config_set.add_argument("--phone-url", default=None, help="MagicDNS/Tailscale Serve URL opened on the phone")
    daily_config_set.add_argument("--port", type=int, default=8787, help="mobile gateway port")
    daily_config_set.add_argument("--proxy-port", type=int, default=18787, help="loopback proxy port for Tailscale Serve")
    daily_config_set.add_argument("--harness-repo", default=None, help="lai harness checkout directory")
    daily_config_set.add_argument("--sandbox-image", default=None, help="digest-pinned Docker image for Harness sandbox work-runs")
    daily_config_set.add_argument("--sandbox-python", default=None, help="bare Python executable inside the sandbox image")
    daily_config_set.add_argument("--path", default=None, help="daily config file path; defaults to ~/.config/lai-gateway/daily.json")
    daily_config_set.add_argument("--json", action="store_true", help="print machine-readable JSON")
    daily_config_show = daily_config_sub.add_parser("show", help="show token-free daily startup defaults")
    daily_config_show.add_argument("--path", default=None, help="daily config file path; defaults to ~/.config/lai-gateway/daily.json")
    daily_config_show.add_argument("--json", action="store_true", help="print machine-readable JSON")
    daily_config_env = daily_config_sub.add_parser("env", help="print shell exports for launchers; contains no token values")
    daily_config_env.add_argument("--path", default=None, help="daily config file path; defaults to ~/.config/lai-gateway/daily.json")
    daily_config_env.add_argument("--json", action="store_true", help="print machine-readable JSON instead of shell exports")

    service_plan_parser = sub.add_parser("service-plan", help="plan a token-free systemd user service for mobile serving")
    service_plan_parser.add_argument("--candidate-ip", required=True, help="private LAN IP for mobile serving")
    service_plan_parser.add_argument("--port", type=int, default=None, help="gateway/mobile port")
    service_plan_parser.add_argument("--service-name", default="lai-gateway-mobile.service", help="systemd user service name")
    service_plan_parser.add_argument("--unit-path", default=None, help="unit file path; defaults to ~/.config/systemd/user/lai-gateway-mobile.service")
    service_plan_parser.add_argument("--python-bin", default=None, help="python executable for ExecStart; defaults to current Python")
    service_plan_parser.add_argument("--repo-dir", default=None, help="working directory/PYTHONPATH for source installs; defaults to cwd")
    service_plan_parser.add_argument("--telegram-notify", action="store_true", help="include startup Telegram notification in ExecStart")
    service_plan_parser.add_argument("--telegram-token-file", default=None, help="telegram token file path for the service command")
    service_plan_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for the service command")
    service_plan_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    service_install_parser = sub.add_parser("service-install", help="write the planned systemd user service without enabling or starting it")
    service_install_parser.add_argument("--candidate-ip", required=True, help="private LAN IP for mobile serving")
    service_install_parser.add_argument("--port", type=int, default=None, help="gateway/mobile port")
    service_install_parser.add_argument("--service-name", default="lai-gateway-mobile.service", help="systemd user service name")
    service_install_parser.add_argument("--unit-path", default=None, help="unit file path; defaults to ~/.config/systemd/user/lai-gateway-mobile.service")
    service_install_parser.add_argument("--python-bin", default=None, help="python executable for ExecStart; defaults to current Python")
    service_install_parser.add_argument("--repo-dir", default=None, help="working directory/PYTHONPATH for source installs; defaults to cwd")
    service_install_parser.add_argument("--telegram-notify", action="store_true", help="include startup Telegram notification in ExecStart")
    service_install_parser.add_argument("--telegram-token-file", default=None, help="telegram token file path for the service command")
    service_install_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for the service command")
    service_install_parser.add_argument("--force", action="store_true", help="overwrite an existing unit file")
    service_install_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    service_remove_parser = sub.add_parser("service-remove", help="remove the systemd user service unit file only")
    service_remove_parser.add_argument("--service-name", default="lai-gateway-mobile.service", help="systemd user service name")
    service_remove_parser.add_argument("--unit-path", default=None, help="unit file path; defaults to ~/.config/systemd/user/lai-gateway-mobile.service")
    service_remove_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    open_ui_parser = sub.add_parser("open-ui", help="print or open the local gateway UI URL")
    open_ui_parser.add_argument("--print-only", action="store_true", help="only print the UI URL")
    stack_parser = sub.add_parser("stack-start", help="start or reuse the local model, harness control plane, and Gateway UI")
    stack_parser.add_argument("--harness-repo", default=None, help="lai harness checkout directory; defaults to sibling checkout or ~/dev/projects/lai-local-agent")
    stack_parser.add_argument("--gateway-port", type=int, default=None, help="Gateway UI port; defaults to LAI_GATEWAY_PORT or 8787")
    stack_parser.add_argument("--log-dir", default=None, help="directory for background service logs; defaults to ~/.local/state/lai-gateway")
    stack_parser.add_argument("--skip-model", action="store_true", help="do not run lai-server-start before starting the stack")
    stack_parser.add_argument("--open", action="store_true", help="open the Gateway UI after the stack is ready")
    stack_parser.add_argument("--check-only", action="store_true", help="print the planned local stack without starting services")
    stack_parser.add_argument("--timeout-seconds", type=float, default=30.0, help="seconds to wait for services to become ready")
    stack_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    dev_parser = sub.add_parser("dev", help="check harness and serve the local gateway UI")
    dev_parser.add_argument("--bind", default=None, help="gateway bind address allowed by config policy")
    dev_parser.add_argument("--port", type=int, default=None, help="gateway port")
    dev_parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    lan_parser = sub.add_parser("lan-info", help="show safe private LAN access candidates without starting a server")
    lan_parser.add_argument("--port", type=int, default=None, help="gateway port for suggested mobile URLs")
    lan_parser.add_argument("--candidate-ip", action="append", default=None, help="override detected candidates with a specific private IP; repeatable")
    lan_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_access_parser = sub.add_parser("mobile-access", help="show phone URLs, WSL/Tailscale hints, and QR data")
    mobile_access_parser.add_argument("--port", type=int, default=None, help="gateway port for mobile URLs")
    mobile_access_parser.add_argument("--bind", default=None, help="gateway bind address used for WSL portproxy hints")
    mobile_access_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_status_parser = sub.add_parser("mobile-status", help="inspect mobile gateway, token, and bridge readiness without starting anything")
    mobile_status_parser.add_argument("--port", type=int, default=None, help="gateway port for mobile access")
    mobile_status_parser.add_argument("--bind", default=None, help="gateway bind address to probe")
    mobile_status_parser.add_argument("--candidate-ip", default=None, help="private LAN IP to probe for an active mobile gateway")
    mobile_status_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_repair_parser = sub.add_parser("mobile-repair", help="repair mobile token and bridge readiness without starting a server")
    mobile_repair_parser.add_argument("--port", type=int, default=None, help="gateway port for mobile access")
    mobile_repair_parser.add_argument("--bind", default=None, help="gateway bind address to probe")
    mobile_repair_parser.add_argument("--candidate-ip", default=None, help="private LAN IP to repair")
    mobile_repair_parser.add_argument("--ttl-seconds", type=int, default=600, help="temporary pair token lifetime, 60..3600 seconds")
    mobile_repair_parser.add_argument("--prepare", action="store_true", help="create/refresh mobile token files")
    mobile_repair_parser.add_argument("--show-pair", action="store_true", help="print the temporary pair token once; requires --prepare")
    mobile_repair_parser.add_argument("--bridge-listen-ip", default=None, help="Windows/Tailscale IPv4 address that the phone will open")
    mobile_repair_parser.add_argument("--bridge-connect-ip", default=None, help="WSL IPv4 address where lai-gateway is bound")
    mobile_repair_parser.add_argument("--apply-bridge", action="store_true", help="apply Windows portproxy/firewall rules")
    mobile_repair_parser.add_argument("--telegram-notify", action="store_true", help="send the repaired mobile access URL to Telegram when explicitly enabled")
    mobile_repair_parser.add_argument("--telegram-token-file", default=None, help="telegram bot token file for --telegram-notify")
    mobile_repair_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for --telegram-notify")
    mobile_repair_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_parser = sub.add_parser("mobile-start", help="prepare or print a safe private mobile access plan")
    mobile_parser.add_argument("--port", type=int, default=None, help="gateway port for suggested mobile URLs")
    mobile_parser.add_argument("--candidate-ip", action="append", default=None, help="override detected candidates with a specific private IP; repeatable")
    mobile_parser.add_argument("--ttl-seconds", type=int, default=600, help="temporary pair token lifetime, 60..3600 seconds")
    mobile_parser.add_argument("--prepare", action="store_true", help="create missing access token and refresh the pair token")
    mobile_parser.add_argument("--show-pair", action="store_true", help="print the temporary pair token once; requires --prepare")
    mobile_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_serve_parser = sub.add_parser("mobile-serve", help="prepare mobile tokens and serve the private LAN gateway")
    mobile_serve_parser.add_argument("--candidate-ip", default=None, help="private LAN IP to bind; required when autodetection is ambiguous")
    mobile_serve_parser.add_argument("--port", type=int, default=None, help="gateway port for mobile access")
    mobile_serve_parser.add_argument("--ttl-seconds", type=int, default=600, help="temporary pair token lifetime, 60..3600 seconds")
    mobile_serve_parser.add_argument("--show-pair", action="store_true", help="print the temporary pair token once before serving")
    mobile_serve_parser.add_argument("--open", action="store_true", help="open the UI in the desktop browser after checks")
    mobile_serve_parser.add_argument("--telegram-notify", action="store_true", help="send the mobile access URL to Telegram before serving; requires Telegram send enable flag")
    mobile_serve_parser.add_argument("--telegram-token-file", default=None, help="telegram bot token file for --telegram-notify")
    mobile_serve_parser.add_argument("--telegram-chat-id", default=None, help="telegram chat id for --telegram-notify")
    bridge_parser = sub.add_parser("mobile-bridge", help="show, apply, or remove Windows-to-WSL mobile port forwarding")
    bridge_parser.add_argument("--port", type=int, default=None, help="gateway port to forward")
    bridge_parser.add_argument("--target", choices=("recommended", "tailscale", "windows-lan"), default="recommended", help="mobile access target to bridge")
    bridge_parser.add_argument("--listen-ip", default=None, help="Windows or Tailscale IPv4 address that the phone will open")
    bridge_parser.add_argument("--connect-ip", default=None, help="WSL IPv4 address where lai-gateway is bound")
    bridge_parser.add_argument("--apply", action="store_true", help="apply Windows portproxy/firewall rules")
    bridge_parser.add_argument("--remove", action="store_true", help="remove Windows portproxy/firewall rules")
    bridge_parser.add_argument("--check", action="store_true", help="run read-only checks for portproxy, firewall, and TCP reachability")
    bridge_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    proxy_parser = sub.add_parser("mobile-proxy", help="serve a loopback-only TCP proxy for Tailscale Serve to reach the mobile gateway")
    proxy_parser.add_argument("--listen-host", default="127.0.0.1", help="loopback host to listen on; defaults to 127.0.0.1")
    proxy_parser.add_argument("--listen-port", type=int, default=18787, help="loopback port to listen on; defaults to 18787")
    proxy_parser.add_argument("--target-host", required=True, help="private WSL/mobile gateway IP to forward to")
    proxy_parser.add_argument("--target-port", type=int, default=8787, help="mobile gateway port to forward to")
    proxy_parser.add_argument("--timeout-seconds", type=float, default=5.0, help="target connection timeout")
    proxy_parser.add_argument("--check", action="store_true", help="check target reachability and listen port without starting the proxy")
    proxy_parser.add_argument("--json", action="store_true", help="print machine-readable JSON for --check")
    token_parser = sub.add_parser("token", help="manage the separate gateway access token")
    token_sub = token_parser.add_subparsers(dest="token_command")
    token_create = token_sub.add_parser("create", help="create a gateway access token file")
    token_create.add_argument("--path", default=None, help="token file path; defaults to ~/.config/lai-gateway/access-token")
    token_create.add_argument("--force", action="store_true", help="overwrite an existing token file")
    token_create.add_argument("--show", action="store_true", help="print the token once for pairing")
    token_create.add_argument("--json", action="store_true", help="print machine-readable JSON")
    token_check = token_sub.add_parser("check", help="validate gateway access token file permissions")
    token_check.add_argument("--path", default=None, help="token file path; defaults to ~/.config/lai-gateway/access-token")
    token_check.add_argument("--json", action="store_true", help="print machine-readable JSON")
    pair_parser = sub.add_parser("pair", help="create and inspect short-lived mobile pairing tokens")
    pair_sub = pair_parser.add_subparsers(dest="pair_command")
    pair_create = pair_sub.add_parser("create", help="create a short-lived gateway pairing token")
    pair_create.add_argument("--path", default=None, help="pair file path; defaults to ~/.config/lai-gateway/pair-token.json")
    pair_create.add_argument("--ttl-seconds", type=int, default=600, help="pairing token lifetime, 60..3600 seconds")
    pair_create.add_argument("--force", action="store_true", help="overwrite an existing pair token file")
    pair_create.add_argument("--show", action="store_true", help="print the pairing token once")
    pair_create.add_argument("--json", action="store_true", help="print machine-readable JSON")
    pair_check = pair_sub.add_parser("check", help="validate the current pairing token file")
    pair_check.add_argument("--path", default=None, help="pair file path; defaults to ~/.config/lai-gateway/pair-token.json")
    pair_check.add_argument("--json", action="store_true", help="print machine-readable JSON")
    pair_revoke = pair_sub.add_parser("revoke", help="delete the current pairing token file")
    pair_revoke.add_argument("--path", default=None, help="pair file path; defaults to ~/.config/lai-gateway/pair-token.json")
    pair_revoke.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_parser = sub.add_parser("telegram", help="configure outbound Telegram notifications safely")
    telegram_sub = telegram_parser.add_subparsers(dest="telegram_command")
    telegram_token_check = telegram_sub.add_parser("token-check", help="diagnose Telegram bot token file without printing it")
    telegram_token_check.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_token_check.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_token_repair = telegram_sub.add_parser("token-repair-whitespace", help="remove accidental whitespace when the compact token shape is valid")
    telegram_token_repair.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_token_repair.add_argument("--dry-run", action="store_true", help="validate repair without rewriting the file")
    telegram_token_repair.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_token_set = telegram_sub.add_parser("token-set", help="write Telegram bot token with 0600 permissions")
    telegram_token_set.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_token_set.add_argument("--stdin", action="store_true", help="read token from stdin instead of a hidden prompt")
    telegram_token_set.add_argument("--force", action="store_true", help="overwrite an existing token file")
    telegram_token_set.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_bot_info = telegram_sub.add_parser("bot-info", help="show the public bot username and id for the configured token")
    telegram_bot_info.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_bot_info.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_chat_check = telegram_sub.add_parser("chat-check", help="diagnose the persisted Telegram chat id without printing it")
    telegram_chat_check.add_argument("--chat-file", default=None, help="telegram chat id file; defaults to ~/.config/lai-gateway/telegram-chat-id")
    telegram_chat_check.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_chat_set = telegram_sub.add_parser("chat-set", help="persist a Telegram chat id with 0600 permissions")
    telegram_chat_set.add_argument("--chat-file", default=None, help="telegram chat id file; defaults to ~/.config/lai-gateway/telegram-chat-id")
    telegram_chat_set.add_argument("--chat-id", required=True, help="numeric Telegram chat id returned by discover-chat")
    telegram_chat_set.add_argument("--force", action="store_true", help="overwrite an existing chat id file")
    telegram_chat_set.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_preflight = telegram_sub.add_parser("preflight", help="check Telegram token/chat configuration without network calls")
    telegram_preflight.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_preflight.add_argument("--chat-id", default=None, help="telegram chat id; defaults to LAI_GATEWAY_TELEGRAM_CHAT_ID")
    telegram_preflight.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_discover = telegram_sub.add_parser("discover-chat", help="fetch recent updates once and print redacted chat id candidates")
    telegram_discover.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_discover.add_argument("--limit", type=int, default=10, help="max update count to inspect, 1..20")
    telegram_discover.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_send = telegram_sub.add_parser("send-message", help="send one outbound Telegram message when explicitly enabled")
    telegram_send.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_send.add_argument("--chat-id", default=None, help="telegram chat id; defaults to LAI_GATEWAY_TELEGRAM_CHAT_ID")
    telegram_send.add_argument("--text", required=True, help="message text to send")
    telegram_send.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_notify = telegram_sub.add_parser("notify-mobile", help="send the current mobile access URL to Telegram when explicitly enabled")
    telegram_notify.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_notify.add_argument("--chat-id", default=None, help="telegram chat id; defaults to LAI_GATEWAY_TELEGRAM_CHAT_ID")
    telegram_notify.add_argument("--port", type=int, default=None, help="gateway port for the mobile URL")
    telegram_notify.add_argument("--bind", default=None, help="gateway bind address used for WSL/Tailscale hints")
    telegram_notify.add_argument("--candidate-ip", default=None, help="WSL/private gateway IP used as the mobile bridge target")
    telegram_notify.add_argument("--json", action="store_true", help="print machine-readable JSON")
    telegram_status = telegram_sub.add_parser("notify-status", help="send current gateway/harness status to Telegram when explicitly enabled")
    telegram_status.add_argument("--token-file", default=None, help="telegram bot token file; defaults to ~/.config/lai-gateway/telegram-bot-token")
    telegram_status.add_argument("--chat-id", default=None, help="telegram chat id; defaults to LAI_GATEWAY_TELEGRAM_CHAT_ID")
    telegram_status.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mcp_parser = sub.add_parser("mcp", help="inspect the harness MCP broker foundation without executing MCP tools")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command")
    mcp_sub.add_parser("status", help="read MCP broker status from the harness")
    mcp_sub.add_parser("tools", help="list declared MCP servers without starting them")
    mcp_policy = mcp_sub.add_parser("policy-check", help="classify an MCP operation without execution")
    mcp_policy.add_argument("--operation", required=True, choices=["status", "list-tools", "call-tool"], help="MCP broker operation to classify")
    mcp_policy.add_argument("--server", default=None, help="declared MCP server name")
    mcp_policy.add_argument("--tool", default=None, help="MCP tool name for call-tool checks")
    sessions_parser = sub.add_parser("sessions", help="manage harness sessions without creating runs")
    sessions_sub = sessions_parser.add_subparsers(dest="sessions_command")
    sessions_list = sessions_sub.add_parser("list", help="list harness sessions")
    sessions_list.add_argument("--limit", type=int, default=20, help="number of sessions to list")
    sessions_sub.add_parser("create", help="create a harness session")
    sessions_get = sessions_sub.add_parser("get", help="read one harness session")
    sessions_get.add_argument("session_id", help="session id returned by sessions create/list")
    sessions_delete = sessions_sub.add_parser("delete", help="delete one harness session")
    sessions_delete.add_argument("session_id", help="session id returned by sessions create/list")
    runs_parser = sub.add_parser("runs", help="manage read-only harness runs")
    runs_sub = runs_parser.add_subparsers(dest="runs_command")
    runs_list = runs_sub.add_parser("list", help="list harness runs")
    runs_list.add_argument("--limit", type=int, default=20, help="number of runs to list")
    runs_create = runs_sub.add_parser("create", help="create a read-only harness run")
    runs_create.add_argument("--mode", required=True, choices=sorted(READ_ONLY_RUN_MODES))
    runs_create.add_argument("--task", required=True, help="read-only task to send to the harness")
    runs_create.add_argument("--session-id", default=None, help="optional persistent session id")
    runs_get = runs_sub.add_parser("get", help="read one harness run")
    runs_get.add_argument("run_id", help="control run id returned by runs create/list")
    runs_events = runs_sub.add_parser("events", help="read bounded metadata-only events for one harness run")
    runs_events.add_argument("run_id", help="control run id returned by runs create/list")
    release_parser = sub.add_parser("release-check", help="check local release readiness")
    release_parser.add_argument("--target", required=True, help="target semantic version, for example 0.1.0")
    release_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    serve_parser = sub.add_parser("serve", help="serve the gateway with configured bind policy")
    serve_parser.add_argument("--bind", default=None, help="gateway bind address allowed by config policy")
    serve_parser.add_argument("--port", type=int, default=None, help="gateway port")
    args = parser.parse_args(argv)

    if args.version:
        print(f"lai-gateway {__version__}")
        return 0
    try:
        if args.command == "daily-config":
            if args.daily_config_command == "set":
                daily = validate_daily_config(
                    candidate_ip=args.candidate_ip,
                    phone_url=args.phone_url,
                    port=args.port,
                    proxy_port=args.proxy_port,
                    harness_repo=args.harness_repo,
                    sandbox_image=args.sandbox_image,
                    sandbox_python=args.sandbox_python,
                    path=Path(args.path).expanduser() if args.path else None,
                )
                target = write_daily_config(daily, path=args.path, force=True)
                payload = collect_daily_config(path=target)
                payload["actions"] = [{"name": "daily_config_written", "path": str(target)}]
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_daily_config(payload))
                return 0 if payload["overall"] == "ready" else 1
            if args.daily_config_command == "show":
                payload = collect_daily_config(path=args.path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_daily_config(payload))
                return 0 if payload["overall"] in {"ready", "needs_config"} else 1
            if args.daily_config_command == "env":
                payload = collect_daily_config(path=args.path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                    return 0 if payload["overall"] == "ready" else 1
                daily = read_daily_config(path=args.path)
                print(shell_exports(daily), end="")
                return 0
            daily_config_parser.print_help()
            return 0
        config = GatewayConfig.from_env()
        if args.command == "ops-status":
            payload = collect_ops_status(
                config=config,
                mobile_candidate_ip=args.candidate_ip,
                mobile_port=args.port,
                telegram_token_file=Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None,
                telegram_chat_id=args.telegram_chat_id,
            )
            if not args.json:
                print(render_ops_status(payload))
                return 0 if payload["overall"] != "blocked" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] != "blocked" else 1
        if args.command == "health-report":
            telegram_token_file = Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None
            payload = collect_health_report(
                config=config,
                mobile_candidate_ip=args.candidate_ip,
                mobile_port=args.port,
                telegram_token_file=telegram_token_file,
                telegram_chat_id=args.telegram_chat_id,
            )
            if args.telegram_notify:
                notify_payload = send_telegram_message(
                    text=render_health_report(payload),
                    token_file=telegram_token_file,
                    chat_id=args.telegram_chat_id,
                )
                payload["telegram_notify"] = {
                    "sent": True,
                    "ok": bool(notify_payload.get("ok", False)),
                    "message_id": notify_payload.get("message_id"),
                    "token_printed": False,
                    "token_included": False,
                    "webhook_exposed": False,
                }
            if not args.json:
                print(render_health_report(payload))
                if args.telegram_notify:
                    print(f"telegram_notify: sent {payload['telegram_notify'].get('message_id')}")
                return 0 if payload["overall"] != "blocked" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] != "blocked" else 1
        if args.command == "model-status":
            payload = collect_model_status(probe_openai=args.probe_openai)
            if not args.json:
                print(render_model_status(payload))
                return 0 if payload["overall"] != "blocked" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] != "blocked" else 1
        if args.command == "model-plan":
            payload = collect_model_plan(backend=args.backend, model_name=args.model_name, base_url=args.base_url)
            if not args.json:
                print(render_model_plan(payload))
                return 0 if payload["overall"] != "blocked" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] != "blocked" else 1
        if args.command == "model-files":
            payload = collect_model_files(paths=args.path, max_results=args.max_results, max_seconds=args.max_seconds)
            if not args.json:
                print(render_model_files(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "model-smoke":
            payload = collect_model_smoke(expected=args.expected, timeout_seconds=args.timeout_seconds, record=args.record, runs_file=Path(args.runs_file).expanduser() if args.runs_file else None)
            if not args.json:
                print(render_model_smoke(payload))
                return 0 if payload["overall"] == "ready" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] == "ready" else 1
        if args.command == "model-task":
            payload = collect_model_task(task=args.task, timeout_seconds=args.timeout_seconds, record=args.record, runs_file=Path(args.runs_file).expanduser() if args.runs_file else None)
            if not args.json:
                print(render_model_task(payload))
                return 0 if payload["overall"] == "ready" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] == "ready" else 1
        if args.command == "model-runs":
            payload = collect_model_runs(path=Path(args.path).expanduser() if args.path else None, limit=args.limit)
            if not args.json:
                print(render_model_runs(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "model-eval":
            payload = collect_model_eval(tasks=tuple(args.task) if args.task else None, timeout_seconds=args.timeout_seconds, record=args.record, runs_file=Path(args.runs_file).expanduser() if args.runs_file else None)
            if not args.json:
                print(render_model_eval(payload))
                return 0 if payload["overall"] == "ready" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] == "ready" else 1
        if args.command == "model-key-create":
            payload = create_model_api_key_file(Path(args.path).expanduser() if args.path else None, force=args.force, include_key=args.show_key)
            if not args.json:
                print(render_model_key(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "model-key-check":
            payload = check_model_api_key_file(Path(args.path).expanduser() if args.path else None)
            if not args.json:
                print(render_model_key(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "service-plan":
            payload = collect_service_plan(
                config=config,
                candidate_ip=args.candidate_ip,
                port=args.port or config.port,
                service_name=args.service_name,
                unit_path=Path(args.unit_path).expanduser() if args.unit_path else None,
                python_bin=args.python_bin,
                repo_dir=Path(args.repo_dir).expanduser() if args.repo_dir else None,
                telegram_notify=args.telegram_notify,
                telegram_token_file=Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None,
                telegram_chat_id=args.telegram_chat_id,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(render_service_plan(payload))
            return 0
        if args.command == "service-install":
            payload = install_service_unit(
                config=config,
                candidate_ip=args.candidate_ip,
                port=args.port or config.port,
                service_name=args.service_name,
                unit_path=Path(args.unit_path).expanduser() if args.unit_path else None,
                python_bin=args.python_bin,
                repo_dir=Path(args.repo_dir).expanduser() if args.repo_dir else None,
                telegram_notify=args.telegram_notify,
                telegram_token_file=Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None,
                telegram_chat_id=args.telegram_chat_id,
                force=args.force,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(render_service_install(payload))
            return 0
        if args.command == "service-remove":
            payload = remove_service_unit(
                service_name=args.service_name,
                unit_path=Path(args.unit_path).expanduser() if args.unit_path else None,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(render_service_remove(payload))
            return 0
        if args.command == "lan-info":
            payload = collect_lan_info(port=args.port or config.port, discovered_hosts=args.candidate_ip)
            if not args.json:
                print(render_lan_info(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "stack-start":
            config = _config_with_overrides(config, None, args.gateway_port)
            payload = start_local_stack(
                config,
                harness_repo=resolve_harness_repo(args.harness_repo),
                gateway_port=args.gateway_port or config.port,
                log_dir=Path(args.log_dir).expanduser() if args.log_dir else None,
                start_model=not args.skip_model,
                open_browser=args.open,
                check_only=args.check_only,
                timeout_seconds=args.timeout_seconds,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(render_local_stack(payload))
            return 0 if payload["overall"] in {"ready", "planned"} else 1
        if args.command == "mobile-access":
            payload = collect_mobile_access(port=args.port or config.port, bind=args.bind or config.bind)
            if not args.json:
                print(render_mobile_access(payload))
                return 0 if payload["candidate_count"] else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["candidate_count"] else 1
        if args.command == "mobile-status":
            payload = collect_mobile_status(
                port=args.port or config.port,
                bind=args.bind or config.bind,
                candidate_ip=args.candidate_ip,
                access_token_path=config.access_token_file,
                pair_token_path=config.pair_token_file,
            )
            if not args.json:
                print(render_mobile_status(payload))
                return 0 if payload["overall"] != "blocked" else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] != "blocked" else 1
        if args.command == "mobile-repair":
            if args.show_pair and not args.prepare:
                raise GatewayError("--show-pair requires --prepare")
            payload = collect_mobile_repair(
                port=args.port or config.port,
                bind=args.bind or config.bind,
                candidate_ip=args.candidate_ip,
                ttl_seconds=args.ttl_seconds,
                prepare=args.prepare,
                show_pair=args.show_pair,
                apply_bridge=args.apply_bridge,
                bridge_listen_ip=args.bridge_listen_ip,
                bridge_connect_ip=args.bridge_connect_ip,
                access_token_path=config.access_token_file,
                pair_token_path=config.pair_token_file,
            )
            if args.telegram_notify:
                after = payload["status_after"]
                notify_payload = notify_mobile_access(
                    port=args.port or config.port,
                    bind=after.get("listener", {}).get("ip") or args.bind or config.bind,
                    token_file=Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None,
                    chat_id=args.telegram_chat_id,
                )
                payload["telegram_notify"] = {"sent": True, "message_id": notify_payload.get("message_id")}
                if not args.json:
                    print(f"telegram_notify: sent {notify_payload.get('message_id')}")
            if not args.json:
                print(render_mobile_repair(payload))
                return 0 if payload["overall"] not in {"blocked", "bridge_failed"} else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] not in {"blocked", "bridge_failed"} else 1
        if args.command == "mobile-start":
            if args.show_pair and not args.prepare:
                raise GatewayError("--show-pair requires --prepare")
            payload = collect_mobile_start(
                port=args.port or config.port,
                ttl_seconds=args.ttl_seconds,
                prepare=args.prepare,
                show_pair=args.show_pair,
                access_token_path=config.access_token_file,
                pair_token_path=config.pair_token_file,
                discovered_hosts=args.candidate_ip,
            )
            if not args.json:
                print(render_mobile_start(payload))
                return 0 if payload["overall"] in {"ready", "needs_prepare"} else 1
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["overall"] in {"ready", "needs_prepare"} else 1
        if args.command == "mobile-proxy":
            if args.check:
                payload = collect_mobile_proxy_status(
                    listen_host=args.listen_host,
                    listen_port=args.listen_port,
                    target_host=args.target_host,
                    target_port=args.target_port,
                    connect_timeout=args.timeout_seconds,
                )
                print(dump_mobile_proxy_json(payload) if args.json else render_mobile_proxy_status(payload))
                return 0 if payload["overall"] in {"ready", "ready_to_start"} else 1
            config = validate_mobile_proxy_config(
                listen_host=args.listen_host,
                listen_port=args.listen_port,
                target_host=args.target_host,
                target_port=args.target_port,
                connect_timeout=args.timeout_seconds,
            )
            run_mobile_proxy(config)
            return 0

        if args.command == "mobile-bridge":
            payload = collect_mobile_bridge(
                port=args.port or config.port,
                listen_ip=args.listen_ip,
                connect_ip=args.connect_ip,
                target=args.target,
                apply=args.apply,
                remove=args.remove,
                check=args.check,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(render_mobile_bridge(payload))
            if payload.get("results") and not all(item.get("ok") for item in payload["results"]):
                return 1
            return 0
        if args.command == "mobile-serve":
            access_path = config.access_token_file or default_access_token_path()
            pair_path = config.pair_token_file or default_pair_token_path()
            payload, serve_config = prepare_mobile_serve_config(
                candidate_ip=args.candidate_ip,
                port=args.port or config.port,
                ttl_seconds=args.ttl_seconds,
                show_pair=args.show_pair,
                access_token_path=access_path,
                pair_token_path=pair_path,
                env={
                    "LAI_GATEWAY_HARNESS_URL": config.harness_url,
                    "LAI_GATEWAY_TOKEN_FILE": str(config.token_file),
                    "LAI_GATEWAY_TIMEOUT_SECONDS": str(config.timeout_seconds),
                },
            )
            if args.telegram_notify:
                notify_payload = notify_mobile_access(
                    port=serve_config.port,
                    bind=serve_config.bind,
                    token_file=Path(args.telegram_token_file).expanduser() if args.telegram_token_file else None,
                    chat_id=args.telegram_chat_id,
                )
                print(f"telegram_notify: sent {notify_payload.get('message_id')}")
            print(render_mobile_serve_ready(payload))
            return _run_dev_stack(serve_config, open_browser=args.open)
        if args.command == "serve":
            config = _config_with_overrides(config, args.bind, args.port)
            serve(config)
            return 0
        if args.command == "dev":
            config = _config_with_overrides(config, args.bind, args.port)
            return _run_dev_stack(config, open_browser=not args.no_open)
        if args.command == "token":
            path = Path(args.path).expanduser() if getattr(args, "path", None) else default_access_token_path()
            if args.token_command == "create":
                payload = create_gateway_access_token(path, force=args.force, include_token=args.show)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"created: {payload['path']}")
                    print(f"mode: {payload['mode']}")
                    print(f"token_length: {payload['token_length']}")
                    if args.show:
                        print(f"token: {payload['token']}")
                return 0
            if args.token_command == "check":
                payload = check_gateway_access_token_file(path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"ok: {payload['path']}")
                    print(f"mode: {payload['mode']}")
                    print(f"token_length: {payload['token_length']}")
                return 0
            token_parser.print_help()
            return 0
        if args.command == "pair":
            default_pair_path = config.pair_token_file or default_pair_token_path()
            path = Path(args.path).expanduser() if getattr(args, "path", None) else default_pair_path
            if args.pair_command == "create":
                payload = create_gateway_pairing_token(
                    path,
                    ttl_seconds=args.ttl_seconds,
                    force=args.force,
                    include_token=args.show,
                    ui_url=_ui_url(config),
                )
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"created: {payload['path']}")
                    print(f"mode: {payload['mode']}")
                    print(f"expires_at: {payload['expires_at']}")
                    print(f"ui: {payload['ui_url']}")
                    if args.show:
                        print(f"token: {payload['token']}")
                return 0
            if args.pair_command == "check":
                payload = check_gateway_pairing_token_file(path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"ok: {payload['path']}")
                    print(f"mode: {payload['mode']}")
                    print(f"expires_at: {payload['expires_at']}")
                    print(f"seconds_remaining: {payload['seconds_remaining']}")
                return 0
            if args.pair_command == "revoke":
                payload = revoke_gateway_pairing_token(path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"revoked: {payload['revoked']} {payload['path']}")
                return 0
            pair_parser.print_help()
            return 0
        if args.command == "telegram":
            token_path = Path(args.token_file).expanduser() if getattr(args, "token_file", None) else None
            if args.telegram_command == "token-check":
                payload = inspect_telegram_token_file(token_file=token_path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_token_check(payload))
                return 0 if payload["ok"] else 1
            if args.telegram_command == "token-repair-whitespace":
                payload = repair_telegram_token_whitespace(token_file=token_path, dry_run=args.dry_run)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_token_repair(payload))
                return 0
            if args.telegram_command == "token-set":
                token_value = sys.stdin.read().strip() if args.stdin else getpass.getpass("Telegram bot token: ").strip()
                payload = write_telegram_token_file(token=token_value, token_file=token_path, force=args.force)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_token_set(payload))
                return 0
            if args.telegram_command == "bot-info":
                payload = get_telegram_bot_info(token_file=token_path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_bot_info(payload))
                return 0
            if args.telegram_command == "chat-check":
                chat_path = Path(args.chat_file).expanduser() if args.chat_file else None
                payload = inspect_telegram_chat_file(chat_file=chat_path)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_chat_check(payload))
                return 0 if payload["ok"] else 1
            if args.telegram_command == "chat-set":
                chat_path = Path(args.chat_file).expanduser() if args.chat_file else None
                payload = write_telegram_chat_file(chat_id=args.chat_id, chat_file=chat_path, force=args.force)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_chat_set(payload))
                return 0
            if args.telegram_command == "preflight":
                payload = collect_telegram_preflight(token_file=token_path, chat_id=args.chat_id)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_preflight(payload))
                return 0 if payload["overall"] in {"ready", "needs_config"} else 1
            if args.telegram_command == "discover-chat":
                payload = discover_telegram_chats(token_file=token_path, limit=args.limit)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(render_telegram_discover(payload))
                return 0
            if args.telegram_command == "send-message":
                payload = send_telegram_message(token_file=token_path, chat_id=args.chat_id, text=args.text)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"sent: {payload.get('message_id')}")
                return 0
            if args.telegram_command == "notify-mobile":
                payload = notify_mobile_access(
                    token_file=token_path,
                    chat_id=args.chat_id,
                    port=args.port or config.port,
                    bind=args.bind or config.bind,
                    candidate_ip=args.candidate_ip,
                )
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"sent_mobile_access: {payload.get('message_id')}")
                return 0
            if args.telegram_command == "notify-status":
                payload = notify_gateway_status(token_file=token_path, chat_id=args.chat_id, config=config)
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(f"sent_status: {payload.get('message_id')}")
                return 0
            telegram_parser.print_help()
            return 0
        payload: dict[str, Any]
        client = HarnessClient(config)
        if args.command == "config":
            payload = {"product": "lai-gateway", "version": __version__, "config": config.public_dict()}
        elif args.command == "contract":
            payload = summarize_contract(client.gateway_contract())
        elif args.command == "status":
            payload = client.status()
        elif args.command == "readiness":
            payload = client.readiness()
        elif args.command == "doctor":
            payload = collect_doctor(config)
            if not args.json:
                print(render_doctor(payload))
                return 0 if payload["overall"] in {"ready", "warn"} else 1
        elif args.command == "open-ui":
            url = _ui_url(config)
            if args.print_only:
                print(url)
            else:
                opened = webbrowser.open(url, new=2)
                print(json.dumps({"product": "lai-gateway", "version": __version__, "url": url, "opened": opened}, indent=2, sort_keys=True))
            return 0
        elif args.command == "mcp":
            if args.mcp_command == "status":
                payload = client.mcp_status()
            elif args.mcp_command == "tools":
                payload = client.mcp_tools()
            elif args.mcp_command == "policy-check":
                payload = client.mcp_policy_check(operation=args.operation, server=args.server, tool=args.tool)
            else:
                mcp_parser.print_help(sys.stderr)
                return 2
        elif args.command == "sessions":
            if args.sessions_command == "list":
                payload = client.list_sessions(args.limit)
            elif args.sessions_command == "create":
                payload = client.create_session()
            elif args.sessions_command == "get":
                payload = client.get_session(args.session_id)
            elif args.sessions_command == "delete":
                payload = client.delete_session(args.session_id)
            else:
                sessions_parser.print_help()
                return 0
        elif args.command == "runs":
            if args.runs_command == "list":
                payload = client.list_runs(args.limit)
            elif args.runs_command == "create":
                payload = client.create_read_only_run(
                    mode=args.mode,
                    task=args.task,
                    session_id=args.session_id,
                )
            elif args.runs_command == "get":
                payload = client.get_run(args.run_id)
            elif args.runs_command == "events":
                payload = client.get_run_events(args.run_id)
            else:
                runs_parser.print_help()
                return 0
        elif args.command == "release-check":
            payload = collect_release_check(args.target, _release_check_repo())
            if not args.json:
                print(render_release_check(payload))
                return 0 if payload["overall"] == "ready" else 1
        else:
            parser.print_help()
            return 0
        print(json.dumps(payload, indent=2, sort_keys=True))
        if args.command == "release-check" and payload["overall"] != "ready":
            return 1
        return 0
    except GatewayError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
