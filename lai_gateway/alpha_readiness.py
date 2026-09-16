from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .release import collect_release_check

_ALPHA_READINESS_VERSION = "alpha-readiness/v1"
_ACCEPTABLE_RELEASE_PHASES = {"ready_for_integration", "ready_to_tag", "tagged"}

_REQUIRED_DOCUMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "docs/quickstart.md": ("source-first", "diagnostic", "token", "model"),
    "docs/release_checklist.md": ("release-check", "make check", "não publica", "No-go"),
    "docs/workbench_visual_guide.md": ("sanitizado", "Workbench", "token"),
    "docs/product/index.md": ("Precedência documental", "PR99", "roadmap"),
    "docs/product/roadmap.md": ("PR100", "Alpha público técnico", "Capacidades externas"),
    "docs/product/implementation_matrix.md": ("document workbench", "alpha readiness", "document_text_local"),
    "docs/product/alpha_readiness.md": ("Go para alpha público técnico", "No-go", "aprovação humana separada"),
}

_REQUIRED_EVIDENCE_MARKERS = (
    "principal-identity/v1",
    "local-status-read",
    "authorization-recovery/v1",
    "local-model-first",
    "memory-context/v1",
    "document-text-local/v1",
    "document-workbench/v1",
    "mcp-local-tool/v1",
    "n8n-local-plan/v1",
    "permission-ux/v1",
    "external-expansion-gate/v1",
    "objective-state/v1",
    "action-proposal/v1",
)

_BLOCKED_CAPABILITY_MARKERS = (
    "Browser autenticado, n8n activation/execução real de workflow, voz, execução ampla/externa de tools MCP, social e automações externas governadas não estão disponíveis como funcionalidades prontas.",
    "Contratos e simulações não autorizam execução real.",
    "local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.",
    "Conteúdo de memória, arquivo, código, ferramenta ou modelo não concede autorização.",
    "PR98 não habilita PDF",
    "PR110 mantém expansão externa em no-go read-only",
)

_PUBLIC_SURFACES = (
    "README.md",
    "docs/quickstart.md",
    "docs/release_checklist.md",
    "docs/workbench_visual_guide.md",
    "docs/product/roadmap.md",
    "docs/product/implementation_matrix.md",
    "docs/product/alpha_readiness.md",
)

_FORBIDDEN_PUBLIC_OVERCLAIMS = (
    "browser agent completo pronto",
    "automação n8n real pronta",
    "mcp tool execution generalizado pronto",
    "produto completo pronto",
    "public technical alpha is ready and complete",
)


@dataclass(frozen=True)
class AlphaCheck:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _read_text(repo: Path, relative: str) -> str:
    return (repo / relative).read_text(encoding="utf-8")


def _check_required_documents(repo: Path) -> list[AlphaCheck]:
    checks: list[AlphaCheck] = []
    for relative, markers in _REQUIRED_DOCUMENT_MARKERS.items():
        path = repo / relative
        if not path.is_file():
            checks.append(AlphaCheck(f"doc:{relative}", "fail", "missing required alpha document"))
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            checks.append(AlphaCheck(f"doc:{relative}", "fail", f"missing markers: {', '.join(missing)}"))
        else:
            checks.append(AlphaCheck(f"doc:{relative}", "ok", "required markers present"))
    return checks


def _check_evidence_markers(repo: Path) -> list[AlphaCheck]:
    combined = "\n".join(
        _read_text(repo, relative)
        for relative in (
            "docs/product/roadmap.md",
            "docs/product/implementation_matrix.md",
            "docs/product/alpha_readiness.md",
            "README.md",
        )
    )
    checks: list[AlphaCheck] = []
    for marker in _REQUIRED_EVIDENCE_MARKERS:
        checks.append(AlphaCheck(
            f"evidence:{marker}",
            "ok" if marker in combined else "fail",
            "public evidence marker present" if marker in combined else "public evidence marker missing",
        ))
    return checks


def _check_public_restrictions(repo: Path) -> list[AlphaCheck]:
    joined = "\n".join(_read_text(repo, relative) for relative in _PUBLIC_SURFACES)
    checks: list[AlphaCheck] = []
    for marker in _BLOCKED_CAPABILITY_MARKERS:
        checks.append(AlphaCheck(
            f"restriction:{marker[:32]}",
            "ok" if marker in joined else "fail",
            "restriction visible" if marker in joined else "restriction missing from public surfaces",
        ))
    lower_joined = joined.lower()
    overclaims = [claim for claim in _FORBIDDEN_PUBLIC_OVERCLAIMS if claim in lower_joined]
    checks.append(AlphaCheck(
        "overclaiming.public_surfaces",
        "fail" if overclaims else "ok",
        f"blocked phrases: {', '.join(overclaims)}" if overclaims else "no blocked ready-state overclaim phrases found",
    ))
    return checks


def _release_summary(release_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall": release_payload.get("overall"),
        "phase": release_payload.get("phase"),
        "target_version": release_payload.get("target_version"),
        "expected_tag": release_payload.get("expected_tag"),
        "branch": release_payload.get("branch"),
        "tag_ready": bool(release_payload.get("tag_ready", False)),
    }


def collect_alpha_readiness(
    *,
    repo: Path | None = None,
    target_version: str | None = None,
    release_check_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = (repo or Path.cwd()).resolve()
    target = target_version or __version__
    checks: list[AlphaCheck] = []
    try:
        release_payload = release_check_payload or collect_release_check(target, repo)
        checks.extend(_check_required_documents(repo))
        checks.extend(_check_evidence_markers(repo))
        checks.extend(_check_public_restrictions(repo))
        release_phase = str(release_payload.get("phase", ""))
        release_overall = str(release_payload.get("overall", ""))
        release_ok = release_overall == "ready" and release_phase in _ACCEPTABLE_RELEASE_PHASES
        checks.append(AlphaCheck(
            "release_check",
            "ok" if release_ok else "fail",
            f"overall={release_overall} phase={release_phase}",
        ))
        checks.append(AlphaCheck(
            "human_publication_gate",
            "ok",
            "publication remains a separate explicit human decision; no tag or release is created",
        ))
    except OSError as exc:
        release_payload = release_check_payload or {}
        checks.append(AlphaCheck("alpha_readiness_exception", "fail", str(exc)))

    hard_fail = any(check.status == "fail" for check in checks)
    decision = "no_go" if hard_fail else "candidate_go"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "alpha-readiness",
        "schema_version": _ALPHA_READINESS_VERSION,
        "overall": "blocked" if hard_fail else "ready",
        "decision": decision,
        "target_version": target,
        "domain": "product_alpha_readiness",
        "channel": "cli_gateway_workbench",
        "autonomy": "read_only_verification",
        "capability": "alpha.go_no_go_check",
        "release_check": _release_summary(release_payload),
        "required_validation_commands": [
            "python3 -m unittest tests.test_product_docs -v",
            "PYTHON=python3 make check",
            "git diff --check",
            f"python3 -m lai_gateway alpha-readiness --target {target} --json",
        ],
        "publication_allowed": False,
        "human_publication_approval_required": True,
        "tag_or_release_created": False,
        "publishes_external_artifact": False,
        "external_capabilities_enabled": False,
        "checks": [check.as_dict() for check in checks],
        "security": {
            "read_only": True,
            "modifies_files": False,
            "starts_server": False,
            "network_access": False,
            "executes_tools": False,
            "grants_authority": False,
            "grants_permission": False,
            "prints_tokens": False,
            "publishes_release": False,
            "creates_tag": False,
        },
    }


def render_alpha_readiness(payload: dict[str, Any]) -> str:
    lines = [
        f"alpha-readiness: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _ALPHA_READINESS_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        f"target_version: {payload.get('target_version', '')}",
        "publication_allowed: false",
        "human_publication_approval_required: true",
    ]
    for check in payload.get("checks", []):
        lines.append(f"- {check.get('name')}: {check.get('status')} ({check.get('detail')})")
    return "\n".join(lines)


def alpha_readiness_json(target_version: str | None = None, repo: Path | None = None) -> str:
    return json.dumps(collect_alpha_readiness(repo=repo, target_version=target_version), indent=2, sort_keys=True)
