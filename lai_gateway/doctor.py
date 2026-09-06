from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from . import __version__
from .config import GatewayConfig, read_control_token, read_gateway_access_token
from .tokens import check_gateway_access_token_file, check_gateway_pairing_token_file
from .contract import summarize_contract
from .errors import GatewayError
from .harness_client import HarnessClient


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _check(status: str, name: str, detail: str) -> DoctorCheck:
    return DoctorCheck(name=name, status=status, detail=detail)


def collect_doctor(config: GatewayConfig | None = None) -> dict[str, Any]:
    checks: list[DoctorCheck] = []
    try:
        config = config or GatewayConfig.from_env()
    except GatewayError as exc:
        return _payload(None, [_check("fail", "config", str(exc))])

    checks.append(_check("ok", "config", "gateway configuration satisfies bind policy"))
    checks.append(_check("ok", "python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))
    checks.append(_check("ok", "gateway_url", f"http://{config.bind}:{config.port}/"))

    try:
        read_control_token(config.token_file)
    except GatewayError as exc:
        checks.append(_check("fail", "token_file", str(exc)))
        return _payload(config, checks)
    checks.append(_check("ok", "token_file", f"readable single-token file: {config.token_file}"))
    if config.private_bind_enabled:
        if config.access_token_file is None:
            checks.append(_check("fail", "access_token_file", "private bind requires LAI_GATEWAY_ACCESS_TOKEN_FILE"))
            return _payload(config, checks)
        try:
            checked = check_gateway_access_token_file(config.access_token_file)
            read_gateway_access_token(config.access_token_file)
        except GatewayError as exc:
            checks.append(_check("fail", "access_token_file", str(exc)))
            return _payload(config, checks)
        checks.append(_check("ok", "access_token_file", f"readable gateway access token file: {config.access_token_file}"))
        checks.append(_check("ok", "access_token_permissions", f"mode={checked['mode']}"))
        if config.pair_token_file is not None and config.pair_token_file.exists():
            try:
                pair = check_gateway_pairing_token_file(config.pair_token_file)
            except GatewayError as exc:
                checks.append(_check("warn", "pair_token_file", str(exc)))
            else:
                checks.append(
                    _check(
                        "ok",
                        "pair_token_file",
                        f"expires_at={pair['expires_at']} seconds_remaining={pair['seconds_remaining']}",
                    )
                )

    client = HarnessClient(config)
    try:
        status = client.status()
    except GatewayError as exc:
        checks.append(_check("fail", "harness_status", str(exc)))
        return _payload(config, checks)
    checks.append(_check("ok", "harness_status", f"version={status.get('version', 'unknown')}"))

    try:
        readiness = client.readiness()
    except GatewayError as exc:
        checks.append(_check("fail", "harness_readiness", str(exc)))
    else:
        overall = readiness.get("overall", "unknown")
        check_status = "ok" if overall == "ready" else "warn"
        checks.append(_check(check_status, "harness_readiness", f"overall={overall}"))

    try:
        contract = summarize_contract(client.gateway_contract())
    except GatewayError as exc:
        checks.append(_check("fail", "gateway_contract", str(exc)))
    else:
        checks.append(
            _check(
                "ok",
                "gateway_contract",
                f"harness={contract.get('version', 'unknown')} routes={contract.get('route_count', 'unknown')}",
            )
        )

    return _payload(config, checks)


def _payload(config: GatewayConfig | None, checks: list[DoctorCheck]) -> dict[str, Any]:
    statuses = {check.status for check in checks}
    overall = "blocked" if "fail" in statuses else "warn" if "warn" in statuses else "ready"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "overall": overall,
        "config": config.public_dict() if config is not None else None,
        "checks": [check.as_dict() for check in checks],
    }


def render_doctor(payload: dict[str, Any]) -> str:
    lines = [
        f"product: {payload['product']}",
        f"version: {payload['version']}",
        f"overall: {payload['overall']}",
    ]
    config = payload.get("config")
    if isinstance(config, dict):
        lines.append(f"gateway_url: http://{config['bind']}:{config['port']}/")
        lines.append(f"harness_url: {config['harness_url']}")
        lines.append(f"access_mode: {config['access_mode']}")
        lines.append(f"token_file: {config['token_file']}")
        if config.get("access_token_file"):
            lines.append(f"access_token_file: {config['access_token_file']}")
    for check in payload["checks"]:
        lines.append(f"- {check['name']}: {check['status']} ({check['detail']})")
    return "\n".join(lines)


def doctor_json(config: GatewayConfig | None = None) -> str:
    return json.dumps(collect_doctor(config), indent=2, sort_keys=True)
