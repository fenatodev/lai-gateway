from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .contract import summarize_contract
from .doctor import collect_doctor, render_doctor
from .errors import GatewayError
from .harness_client import READ_ONLY_RUN_MODES, HarnessClient
from .lan import collect_lan_info, render_lan_info
from .mobile import collect_mobile_start, render_mobile_start
from .release import collect_release_check, render_release_check
from .server import serve
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
    open_ui_parser = sub.add_parser("open-ui", help="print or open the local gateway UI URL")
    open_ui_parser.add_argument("--print-only", action="store_true", help="only print the UI URL")
    dev_parser = sub.add_parser("dev", help="check harness and serve the local gateway UI")
    dev_parser.add_argument("--bind", default=None, help="gateway bind address allowed by config policy")
    dev_parser.add_argument("--port", type=int, default=None, help="gateway port")
    dev_parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    lan_parser = sub.add_parser("lan-info", help="show safe private LAN access candidates without starting a server")
    lan_parser.add_argument("--port", type=int, default=None, help="gateway port for suggested mobile URLs")
    lan_parser.add_argument("--candidate-ip", action="append", default=None, help="override detected candidates with a specific private IP; repeatable")
    lan_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    mobile_parser = sub.add_parser("mobile-start", help="prepare or print a safe private mobile access plan")
    mobile_parser.add_argument("--port", type=int, default=None, help="gateway port for suggested mobile URLs")
    mobile_parser.add_argument("--candidate-ip", action="append", default=None, help="override detected candidates with a specific private IP; repeatable")
    mobile_parser.add_argument("--ttl-seconds", type=int, default=600, help="temporary pair token lifetime, 60..3600 seconds")
    mobile_parser.add_argument("--prepare", action="store_true", help="create missing access token and refresh the pair token")
    mobile_parser.add_argument("--show-pair", action="store_true", help="print the temporary pair token once; requires --prepare")
    mobile_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
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
    sessions_parser = sub.add_parser("sessions", help="manage harness sessions without creating runs")
    sessions_sub = sessions_parser.add_subparsers(dest="sessions_command")
    sessions_list = sessions_sub.add_parser("list", help="list harness sessions")
    sessions_list.add_argument("--limit", type=int, default=20, help="number of sessions to list")
    sessions_sub.add_parser("create", help="create a harness session")
    sessions_get = sessions_sub.add_parser("get", help="read one harness session")
    sessions_get.add_argument("session_id", help="session id returned by sessions create/list")
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
        config = GatewayConfig.from_env()
        if args.command == "lan-info":
            payload = collect_lan_info(port=args.port or config.port, discovered_hosts=args.candidate_ip)
            if not args.json:
                print(render_lan_info(payload))
                return 0
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
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
        elif args.command == "sessions":
            if args.sessions_command == "list":
                payload = client.list_sessions(args.limit)
            elif args.sessions_command == "create":
                payload = client.create_session()
            elif args.sessions_command == "get":
                payload = client.get_session(args.session_id)
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
            else:
                runs_parser.print_help()
                return 0
        elif args.command == "release-check":
            payload = collect_release_check(args.target)
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
