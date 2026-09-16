from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__

IDENTITY_BINDING_VERSION = "principal-identity/v1"
DEFAULT_USER_ID = "local-user"
DEFAULT_CLIENT_ID = "local-cli"
DEFAULT_AGENT_ID = "lai-agent"
DEFAULT_SERVICE_ID = "lai-gateway"
TRUSTED_IDENTITY_SOURCES = {
    "local-cli",
    "gateway-loopback",
    "workbench-loopback",
    "private-gateway-token",
    "test-fixture",
}
_SECRET_MARKERS = (
    "bearer ",
    "authorization:",
    "api_key=",
    "apikey=",
    "password=",
    "secret=",
    "token=",
    "ghp_",
    "github_pat_",
    "sk-",
    "xoxb-",
    "xoxp-",
)


@dataclass(frozen=True)
class PrincipalIdentity:
    identity_binding_id: str
    status: str
    reason: str
    user_id: str
    client_id: str
    agent_id: str
    service_id: str
    identity_source: str
    source_trusted: bool
    identity_verified: bool
    expected_identity_binding_id: str | None
    identity_drift: bool
    rejected_claims: tuple[str, ...]
    identity_version: str
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rejected_claims"] = list(self.rejected_claims)
        return payload


def _safe_label(value: str | None, *, default: str, limit: int = 96) -> str:
    text = (value or default).strip()
    if not text:
        text = default
    lowered = text.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        return "[redacted]"
    return text[:limit]


def _identity_binding_id(*, user_id: str, client_id: str, agent_id: str, service_id: str, source: str) -> str:
    material = "|".join((IDENTITY_BINDING_VERSION, user_id, client_id, agent_id, service_id, source))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"pid-{digest}"


def build_principal_identity(
    *,
    user_id: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    service_id: str | None = None,
    identity_source: str | None = None,
    expected_identity_binding_id: str | None = None,
    claimed_user_id: str | None = None,
    claimed_client_id: str | None = None,
    claimed_agent_id: str | None = None,
    claimed_service_id: str | None = None,
) -> PrincipalIdentity:
    actual_user = _safe_label(user_id, default=DEFAULT_USER_ID)
    actual_client = _safe_label(client_id, default=DEFAULT_CLIENT_ID)
    actual_agent = _safe_label(agent_id, default=DEFAULT_AGENT_ID)
    actual_service = _safe_label(service_id, default=DEFAULT_SERVICE_ID)
    source = _safe_label(identity_source, default="local-cli")
    binding_id = _identity_binding_id(
        user_id=actual_user,
        client_id=actual_client,
        agent_id=actual_agent,
        service_id=actual_service,
        source=source,
    )
    rejected: list[str] = []
    claims = {
        "user_id": claimed_user_id,
        "client_id": claimed_client_id,
        "agent_id": claimed_agent_id,
        "service_id": claimed_service_id,
    }
    actual = {
        "user_id": actual_user,
        "client_id": actual_client,
        "agent_id": actual_agent,
        "service_id": actual_service,
    }
    for key, raw_claim in claims.items():
        if raw_claim is None:
            continue
        claim = _safe_label(raw_claim, default="")
        if claim != actual[key]:
            rejected.append(key)

    source_trusted = source in TRUSTED_IDENTITY_SOURCES
    expected = _safe_label(expected_identity_binding_id, default="") or None
    drift = bool(expected and expected != binding_id)
    verified = source_trusted and not rejected and not drift
    reason = "identity binding verified from trusted source"
    status = "verified"
    if not source_trusted:
        status = "blocked"
        reason = "identity source is not trusted"
    elif rejected:
        status = "blocked"
        reason = "claimed identity does not match trusted principal binding"
    elif drift:
        status = "blocked"
        reason = "identity binding drift detected"

    return PrincipalIdentity(
        identity_binding_id=binding_id,
        status=status,
        reason=reason,
        user_id=actual_user,
        client_id=actual_client,
        agent_id=actual_agent,
        service_id=actual_service,
        identity_source=source,
        source_trusted=source_trusted,
        identity_verified=verified,
        expected_identity_binding_id=expected,
        identity_drift=drift,
        rejected_claims=tuple(rejected),
        identity_version=IDENTITY_BINDING_VERSION,
    )


def collect_identity_binding(**kwargs: str | None) -> dict[str, Any]:
    identity = build_principal_identity(**kwargs)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "identity-binding",
        "overall": "ready",
        "identity_version": IDENTITY_BINDING_VERSION,
        "identity_verified": identity.identity_verified,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "external_side_effects": False,
        "grants_permission": False,
        "identity": identity.to_dict(),
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "identity_elevates_permissions": False,
            "content_elevates_permissions": False,
            "channels_elevate_permissions": False,
        },
    }


def render_identity_binding(payload: dict[str, Any]) -> str:
    identity = payload["identity"]
    return "\n".join(
        [
            f"lai-gateway identity-binding: {payload['overall']}",
            f"version: {payload['version']}",
            f"identity_version: {payload['identity_version']}",
            f"identity_binding_id: {identity['identity_binding_id']}",
            f"status: {identity['status']}",
            f"identity_source: {identity['identity_source']}",
            f"source_trusted: {str(identity['source_trusted']).lower()}",
            f"identity_verified: {str(identity['identity_verified']).lower()}",
            f"identity_drift: {str(identity['identity_drift']).lower()}",
            f"rejected_claims: {len(identity.get('rejected_claims', []))}",
            f"reason: {identity['reason']}",
            "grants_permissions: false",
            "executes_tools: false",
        ]
    )
