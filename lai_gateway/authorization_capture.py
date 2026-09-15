from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapter_dry_run import collect_adapter_dry_run

_AUTHORIZATION_CAPTURE_VERSION = "authorization-capture-stub/v1"
_SENSITIVE_HINTS = ("bearer", "password", "secret", "token", "api_key", "apikey")


@dataclass(frozen=True)
class AuthorizationCaptureStub:
    capture_id: str
    status: str
    reason: str
    adapter_id: str | None
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action: str
    approval_intent: bool
    approved_by: str
    dry_run_id: str
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    decision_outcome: str
    authorization_status: str
    proposal_status: str
    dry_run_status: str
    requires_human_approval: bool
    approval_captured: bool
    approval_validated: bool
    effective_authorization: bool
    capture_persisted: bool
    capture_version: str
    dispatch_enabled: bool = False
    adapter_dispatched: bool = False
    adapter_executed: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    grants_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _capture_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"acs-{digest}"


def _safe_label(value: str | None, *, default: str, limit: int = 96) -> str:
    text = (value or default).strip()
    if not text:
        text = default
    lowered = text.lower()
    if any(hint in lowered for hint in _SENSITIVE_HINTS):
        return "[redacted]"
    return text[:limit]


def _capture_status(dry_run: dict[str, Any], approval_intent: bool) -> tuple[str, str, bool]:
    if dry_run.get("status") == "blocked":
        return "blocked", "capture refused because the dry-run is blocked", False
    if not dry_run.get("requires_human_approval"):
        return "not_required", "capture not required for this non-effective path", False
    if not approval_intent:
        return "pending", "explicit human approval has not been captured", False
    return "captured_non_effective", "explicit approval captured as a stub without effective authorization", True


def build_authorization_capture_stub(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
) -> tuple[AuthorizationCaptureStub, dict[str, Any]]:
    dry_run_payload = collect_adapter_dry_run(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
    )
    dry_run = dry_run_payload["dry_run"]
    status, reason, captured = _capture_status(dry_run, approval_intent)
    safe_approved_by = _safe_label(approved_by, default="user")
    parts = (
        _AUTHORIZATION_CAPTURE_VERSION,
        dry_run["dry_run_id"],
        dry_run["proposal_id"],
        dry_run["authorization_record_id"],
        dry_run["evaluation_id"],
        dry_run["decision_id"],
        status,
        str(approval_intent).lower(),
        safe_approved_by,
    )
    capture_id = _capture_id(parts)
    stub = AuthorizationCaptureStub(
        capture_id=capture_id,
        status=status,
        reason=reason,
        adapter_id=dry_run.get("adapter_id"),
        requested_capability=dry_run["requested_capability"],
        actor=dry_run["actor"],
        channel=dry_run["channel"],
        domain=dry_run["domain"],
        action=dry_run["action"],
        approval_intent=approval_intent,
        approved_by=safe_approved_by,
        dry_run_id=dry_run["dry_run_id"],
        proposal_id=dry_run["proposal_id"],
        authorization_record_id=dry_run["authorization_record_id"],
        evaluation_id=dry_run["evaluation_id"],
        decision_id=dry_run["decision_id"],
        audit_log_id=dry_run["audit_log_id"],
        decision_outcome=dry_run["decision_outcome"],
        authorization_status=dry_run["authorization_status"],
        proposal_status=dry_run["proposal_status"],
        dry_run_status=dry_run["status"],
        requires_human_approval=bool(dry_run["requires_human_approval"]),
        approval_captured=captured,
        approval_validated=False,
        effective_authorization=False,
        capture_persisted=False,
        capture_version=_AUTHORIZATION_CAPTURE_VERSION,
        dispatch_enabled=False,
    )
    return stub, dry_run_payload


def collect_authorization_capture_stub(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
) -> dict[str, Any]:
    stub, dry_run_payload = build_authorization_capture_stub(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "authorization-capture-stub",
        "overall": "ready",
        "capture_version": _AUTHORIZATION_CAPTURE_VERSION,
        "capture_persisted": False,
        "approval_validated": False,
        "effective_authorization": False,
        "dispatch_enabled": False,
        "executes_tools": False,
        "external_side_effects": False,
        "capture": stub.to_dict(),
        "dry_run": dry_run_payload["dry_run"],
        "audit": dry_run_payload["audit"],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "capture_elevates_permissions": False,
            "approval_text_elevates_permissions": False,
            "persists_authorization": False,
            "dispatches_adapter": False,
        },
    }


def render_authorization_capture_stub(payload: dict[str, Any]) -> str:
    capture = payload["capture"]
    lines = [
        f"lai-gateway authorization-capture-stub: {payload['overall']}",
        f"version: {payload['version']}",
        f"capture_version: {payload['capture_version']}",
        f"capture_id: {capture['capture_id']}",
        f"status: {capture['status']}",
        f"adapter_id: {capture.get('adapter_id') or 'none'}",
        f"requested_capability: {capture['requested_capability']}",
        f"approval_intent: {str(capture['approval_intent']).lower()}",
        f"approval_captured: {str(capture['approval_captured']).lower()}",
        f"approval_validated: {str(capture['approval_validated']).lower()}",
        f"effective_authorization: {str(capture['effective_authorization']).lower()}",
        f"capture_persisted: {str(capture['capture_persisted']).lower()}",
        f"dispatch_enabled: {str(capture['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(capture['adapter_dispatched']).lower()}",
        f"executes_tools: {str(capture['executes_tools']).lower()}",
        f"reason: {capture['reason']}",
        "grants_permissions: false",
        "stub_only: true",
    ]
    return "\n".join(lines)
