from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .config import GatewayConfig
from .contract import summarize_contract
from .errors import GatewayError
from .harness_client import READ_ONLY_RUN_MODES, HarnessClient
from .release import collect_release_check, render_release_check
from .server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lai-gateway")
    parser.add_argument("--version", action="store_true", help="print gateway version and exit")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("config", help="print non-secret gateway configuration")
    sub.add_parser("contract", help="fetch and validate the harness gateway contract")
    sub.add_parser("status", help="fetch harness status through the gateway client")
    sub.add_parser("readiness", help="fetch harness readiness through the gateway client")
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
    serve_parser = sub.add_parser("serve", help="serve the loopback-only gateway MVP")
    serve_parser.add_argument("--bind", default=None, help="loopback bind address")
    serve_parser.add_argument("--port", type=int, default=None, help="gateway port")
    args = parser.parse_args(argv)

    if args.version:
        print(f"lai-gateway {__version__}")
        return 0
    try:
        config = GatewayConfig.from_env()
        if args.command == "serve":
            if args.bind is not None or args.port is not None:
                config = GatewayConfig(
                    harness_url=config.harness_url,
                    token_file=config.token_file,
                    bind=args.bind or config.bind,
                    port=args.port or config.port,
                    timeout_seconds=config.timeout_seconds,
                )
                config = GatewayConfig.from_env(
                    {
                        "LAI_GATEWAY_HARNESS_URL": config.harness_url,
                        "LAI_GATEWAY_TOKEN_FILE": str(config.token_file),
                        "LAI_GATEWAY_BIND": config.bind,
                        "LAI_GATEWAY_PORT": str(config.port),
                        "LAI_GATEWAY_TIMEOUT_SECONDS": str(config.timeout_seconds),
                    }
                )
            serve(config)
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
