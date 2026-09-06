from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .config import GatewayConfig
from .contract import summarize_contract
from .errors import GatewayError
from .harness_client import HarnessClient
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
