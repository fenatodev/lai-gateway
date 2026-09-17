from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .external_expansion import collect_external_expansion_gate
from .public_browser import collect_public_browser

_SCHEMA_VERSION = "external-capability-gate/v1"
_DEFAULT_CANDIDATE = "browser.public_source_inspection"


@dataclass(frozen=True)
class Candidate:
    id: str
    label: str
    domain: str
    channel: str
    autonomy: str
    capability: str
    effect: str
    risk: str
    selected_path: str


@dataclass(frozen=True)
class CandidateCheck:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


_CANDIDATES: dict[str, Candidate] = {
    "browser.public_source_inspection": Candidate(
        id="browser.public_source_inspection",
        label="public source inspection",
        domain="web_public_read",
        channel="gateway_cli_workbench",
        autonomy="one_explicit_public_url_per_request",
        capability="browser.inspect_public_source",
        effect="bounded public GET only when the separate inspect action is invoked",
        risk="remote content is untrusted and can contain prompt injection or misleading links",
        selected_path="governed public read-only path from PR119",
    ),
    "browser.authenticated_session": Candidate(
        id="browser.authenticated_session",
        label="authenticated browser session",
        domain="web_authenticated",
        channel="not_enabled",
        autonomy="blocked",
        capability="browser.authenticated_session",
        effect="would use cookies or logged-in browser state",
        risk="credential/session exfiltration, CSRF, form submission and account mutation",
        selected_path="blocked sensitive path",
    ),
    "n8n.execute_workflow": Candidate(
        id="n8n.execute_workflow",
        label="real n8n workflow execution",
        domain="automation_external",
        channel="not_enabled",
        autonomy="blocked",
        capability="n8n.execute_workflow",
        effect="would call a real workflow or webhook",
        risk="persistent automation, credentials, network calls and external side effects",
        selected_path="blocked sensitive path",
    ),
    "mcp.call_tool": Candidate(
        id="mcp.call_tool",
        label="broad MCP tool call",
        domain="tool_execution_external",
        channel="not_enabled",
        autonomy="blocked",
        capability="mcp.call_tool",
        effect="would execute an arbitrary tool behind a broker",
        risk="tool-specific authority cannot be inferred from MCP metadata",
        selected_path="blocked sensitive path",
    ),
    "social_career.send_message": Candidate(
        id="social_career.send_message",
        label="governed outbound message",
        domain="external_messaging",
        channel="not_enabled",
        autonomy="blocked",
        capability="social_career.send_message",
        effect="would send text to a real external recipient",
        risk="wrong recipient, reputational effect and unreviewed content",
        selected_path="blocked sensitive path",
    ),
}

_SENSITIVE_BLOCKERS: dict[str, tuple[str, ...]] = {
    "browser.authenticated_session": (
        "missing isolated browser profile contract",
        "missing cookie/session containment",
        "missing credential handling policy",
        "missing form/click/download negative tests",
        "missing per-site human approval envelope",
    ),
    "n8n.execute_workflow": (
        "missing n8n instance executor contract",
        "missing workflow activation/execution containment",
        "missing credential and webhook policy",
        "missing replay/idempotency tests for workflow side effects",
        "missing human approval for workflow, inputs and consequences",
    ),
    "mcp.call_tool": (
        "missing per-tool capability registry",
        "missing broker/tool allowlist with executor-specific policy",
        "missing argument schema and output redaction contract",
        "missing negative tests for shell, network, files and credentials",
        "missing grant consumption path bound to tool and parameters",
    ),
    "social_career.send_message": (
        "missing durable approval by content and destination",
        "missing recipient identity verification",
        "missing anti-duplicate send guard",
        "missing audit/recovery semantics for external sends",
        "missing human approval for final message body",
    ),
}


def _read_text(repo: Path, relative: str) -> str:
    try:
        return (repo / relative).read_text(encoding="utf-8")
    except OSError:
        return ""


def _marker_check(repo: Path, relative: str, markers: tuple[str, ...]) -> CandidateCheck:
    text = _read_text(repo, relative)
    missing = [marker for marker in markers if marker not in text]
    return CandidateCheck(
        f"doc:{relative}",
        "fail" if missing else "ok",
        f"missing markers: {', '.join(missing)}" if missing else "required markers present",
    )


def _default_candidate_checks(repo: Path) -> tuple[list[CandidateCheck], dict[str, Any]]:
    checks = [
        _marker_check(repo, "docs/product/pr_119_public_browser_v2.md", (
            "public-browser-inspector/v1",
            "source inspector público restrito",
            "Não habilita browser autenticado",
            "Não segue links",
            "Não executa tools",
        )),
        _marker_check(repo, "docs/product/public_browser_inspector.md", (
            "public-browser-inspector/v1",
            "links públicos como strings inertes",
            "Sem autorização efetiva",
        )),
        _marker_check(repo, "tests/test_public_browser.py", (
            "test_inspect_public_source_extracts_links_without_following",
            "links_followed",
            "uses_cookies",
            "credentialed_access",
        )),
        _marker_check(repo, "tests/test_ui.py", (
            "test_gateway_public_browser_inspector_endpoint_is_read_only_and_secret_free",
            "public-browser-inspector/v1",
        )),
    ]
    plan_payload = collect_public_browser(url="https://example.com/", browser_action="plan")
    checks.append(CandidateCheck(
        "runtime:public_browser_plan_no_network",
        "ok" if not plan_payload.get("fetch_attempted") and not plan_payload.get("network_calls") else "fail",
        "planning the candidate does not fetch, follow links, use credentials or mutate state",
    ))
    checks.append(CandidateCheck(
        "authorization:per_request_url_only",
        "ok",
        "candidate requires one explicit public URL per request; this gate does not grant durable authority",
    ))
    runtime = {
        "public_browser_plan": {
            "schema_version": plan_payload.get("schema_version"),
            "overall": plan_payload.get("overall"),
            "browser_action": plan_payload.get("browser_action"),
            "fetch_attempted": bool(plan_payload.get("fetch_attempted")),
            "network_calls": bool(plan_payload.get("network_calls")),
            "uses_cookies": bool(plan_payload.get("uses_cookies")),
            "credentialed_access": bool(plan_payload.get("credentialed_access")),
            "external_side_effects": bool(plan_payload.get("external_side_effects")),
        }
    }
    return checks, runtime


def _sensitive_candidate_checks(candidate_id: str) -> tuple[list[CandidateCheck], dict[str, Any]]:
    blockers = _SENSITIVE_BLOCKERS.get(candidate_id, ("candidate is not implemented by a contained executor",))
    checks = [CandidateCheck(f"blocker:{idx + 1}", "fail", blocker) for idx, blocker in enumerate(blockers)]
    return checks, {"blocked_missing_evidence": list(blockers)}


def _candidate_payload(candidate: Candidate) -> dict[str, str]:
    return {
        "id": candidate.id,
        "label": candidate.label,
        "domain": candidate.domain,
        "channel": candidate.channel,
        "autonomy": candidate.autonomy,
        "capability": candidate.capability,
        "effect": candidate.effect,
        "risk": candidate.risk,
        "selected_path": candidate.selected_path,
    }


def collect_external_capability_gate(*, repo: Path | None = None, candidate: str = _DEFAULT_CANDIDATE) -> dict[str, Any]:
    repo = (repo or Path.cwd()).resolve()
    candidate_id = (candidate or _DEFAULT_CANDIDATE).strip()
    selected = _CANDIDATES.get(candidate_id)
    if selected is None:
        selected = Candidate(
            id=candidate_id or "<missing>",
            label="unknown candidate",
            domain="unknown",
            channel="not_enabled",
            autonomy="blocked",
            capability="unknown",
            effect="unknown",
            risk="unknown candidate cannot be evaluated safely",
            selected_path="blocked unknown path",
        )
        candidate_checks, runtime_evidence = ([CandidateCheck("candidate:known", "fail", "candidate is not in the explicit PR120 catalog")], {})
    elif candidate_id == _DEFAULT_CANDIDATE:
        candidate_checks, runtime_evidence = _default_candidate_checks(repo)
    else:
        candidate_checks, runtime_evidence = _sensitive_candidate_checks(candidate_id)

    baseline = collect_external_expansion_gate(repo=repo)
    baseline_security = baseline.get("security", {}) if isinstance(baseline.get("security"), dict) else {}
    baseline_ok = (
        not bool(baseline.get("external_expansion_allowed"))
        and not bool(baseline.get("external_capabilities_enabled"))
        and not bool(baseline_security.get("uses_credentials"))
        and not bool(baseline_security.get("executes_tools"))
        and not bool(baseline_security.get("dispatches_adapter"))
        and not bool(baseline_security.get("issues_grants"))
        and not bool(baseline_security.get("consumes_grants"))
    )
    checks = [CandidateCheck(
        "baseline:external_expansion_gate",
        "ok" if baseline_ok else "fail",
        "PR110 baseline keeps broad external expansion blocked" if baseline_ok else "external expansion baseline is not fail-closed",
    )]
    checks.extend(candidate_checks)
    hard_fail = any(check.status == "fail" for check in checks)
    selected_candidate_go = selected.id == _DEFAULT_CANDIDATE and not hard_fail
    decision = "go_for_limited_public_read_only_candidate" if selected_candidate_go else "no_go_for_selected_candidate"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "external-capability-gate",
        "schema_version": _SCHEMA_VERSION,
        "overall": "ready" if selected_candidate_go else "blocked",
        "decision": decision,
        "summary": "PR120 selects only the restricted public source inspector as the first candidate; sensitive external capabilities remain blocked.",
        "candidate": _candidate_payload(selected),
        "selected_candidate_go": selected_candidate_go,
        "selected_candidate_enabled_by_gate": False,
        "external_capability_enabled": False,
        "external_runtime_enabled": False,
        "gate_only": True,
        "read_only": True,
        "proposal_only": True,
        "effective_authorization": False,
        "baseline_external_expansion": {
            "schema_version": baseline.get("schema_version"),
            "overall": baseline.get("overall"),
            "decision": baseline.get("decision"),
            "external_expansion_allowed": bool(baseline.get("external_expansion_allowed")),
            "external_capabilities_enabled": bool(baseline.get("external_capabilities_enabled")),
        },
        "runtime_evidence": runtime_evidence,
        "required_before_sensitive_go": [
            "executor-specific containment",
            "identity-bound action envelope",
            "least-privilege capability allowlist",
            "single-use grant only after explicit human approval when an effect is real",
            "negative tests for credentials, replay, duplicate effects, private data and unsafe targets",
            "public docs and matrix updated without overclaiming",
        ],
        "blocked_sensitive_candidates": [
            "browser.authenticated_session",
            "n8n.execute_workflow",
            "mcp.call_tool",
            "social_career.send_message",
        ],
        "checks": [check.as_dict() for check in checks],
        "security": {
            "read_only": True,
            "modifies_files": False,
            "starts_server": False,
            "network_access": False,
            "uses_authenticated_browser": False,
            "uses_browser_profile": False,
            "uses_cookies": False,
            "executes_javascript": False,
            "submits_forms": False,
            "downloads_files": False,
            "follows_links": False,
            "uses_credentials": False,
            "calls_n8n_instance": False,
            "activates_workflow": False,
            "executes_workflow": False,
            "calls_mcp_broker": False,
            "executes_tools": False,
            "dispatches_adapter": False,
            "issues_grants": False,
            "consumes_grants": False,
            "sends_messages": False,
            "publishes": False,
            "external_side_effects": False,
            "prints_tokens": False,
        },
    }


def render_external_capability_gate(payload: dict[str, Any]) -> str:
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    lines = [
        f"lai-gateway external-capability-gate: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        f"candidate: {candidate.get('id', 'unknown')}",
        f"capability: {candidate.get('capability', 'unknown')}",
        f"selected_candidate_go: {str(bool(payload.get('selected_candidate_go'))).lower()}",
        "selected_candidate_enabled_by_gate: false",
        "external_capability_enabled: false",
        "effective_authorization: false",
        "read_only: true",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
    ]
    blocked = payload.get("blocked_sensitive_candidates") if isinstance(payload.get("blocked_sensitive_candidates"), list) else []
    if blocked:
        lines.append("blocked_sensitive_candidates:")
        for item in blocked[:8]:
            lines.append(f"  - {item}")
    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    if checks:
        lines.append("checks:")
        for check in checks:
            lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")
    return "\n".join(lines)
