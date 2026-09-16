from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .mcp_local_tool import collect_mcp_local_tool
from .n8n_local_plan import collect_n8n_local_plan
from .permission_ux import collect_permission_ux
from .public_browser import collect_public_browser

_SCHEMA_VERSION = "external-expansion-gate/v1"

_BLOCKED_EXTERNAL_CAPABILITIES: tuple[dict[str, str], ...] = (
    {"capability": "browser.authenticated_session", "reason": "exige isolamento de perfil, cookies e aprovação humana própria"},
    {"capability": "browser.form_submit", "reason": "submete dados externos e precisa de revisão de conteúdo/alvo"},
    {"capability": "n8n.activate_workflow", "reason": "pode manter automação ativa após a interação"},
    {"capability": "n8n.execute_workflow", "reason": "pode chamar rede, credenciais, webhooks e efeitos externos"},
    {"capability": "mcp.call_tool", "reason": "execução ampla depende da tool e não é equivalente a metadata"},
    {"capability": "credentials.use", "reason": "uso de segredo requer escopo, armazenamento e auditoria próprios"},
    {"capability": "social_career.send_message", "reason": "envio externo exige conteúdo, destino e aprovação explícitos"},
    {"capability": "social_career.publish_post", "reason": "publicação é efeito externo e reputacional"},
    {"capability": "social_career.submit_application", "reason": "candidatura/formulário altera estado fora do LAI"},
    {"capability": "voice.capture_microphone", "reason": "captura contínua exige consentimento, retenção e limites próprios"},
    {"capability": "voice.invoke_action", "reason": "canal de voz não eleva permissão de execução"},
    {"capability": "document.ocr", "reason": "processamento amplo de documentos/mídia ainda não está contido"},
    {"capability": "media.upload_external", "reason": "upload externo movimenta dados privados para outro serviço"},
    {"capability": "webhook_trigger", "reason": "webhooks podem produzir efeitos remotos assíncronos"},
    {"capability": "publication.release_or_announcement", "reason": "tag, release e anúncio público exigem decisão humana separada"},
)

_EXTERNAL_ENABLE_FLAGS = (
    "executes_tools",
    "grants_permissions",
    "network_access_enabled",
    "credentialed_access_enabled",
    "external_side_effects_enabled",
    "workflow_execution_enabled",
    "workflow_activation_enabled",
    "webhook_execution_enabled",
    "calls_n8n_instance",
    "audio_capture_enabled",
    "wake_word_enabled",
    "publication_enabled",
    "message_sending_enabled",
    "application_submission_enabled",
    "form_submission_enabled",
    "model_download_enabled",
    "benchmark_execution_enabled",
    "runtime_mutation_enabled",
    "document_ingestion_enabled",
    "ocr_enabled",
    "transcription_enabled",
    "external_upload_enabled",
    "destructive_processing_enabled",
)

_REQUIRED_DOC_MARKERS: dict[str, tuple[str, ...]] = {
    "docs/product/post_pr100_roadmap.md": (
        "PR110",
        "Go/no-go para capacidades externas",
        "publicação humana separada",
    ),
    "docs/product/implementation_matrix.md": (
        "Browser autenticado",
        "n8n activation/execução real de workflow",
        "MCP amplo",
        "Telegram outbound tem limite conhecido",
    ),
    "docs/product/alpha_readiness.md": (
        "PR110 mantém expansão externa em no-go read-only",
        "capacidades externas",
    ),
    "README.md": (
        "external-expansion-gate/v1",
        "external expansion gate",
    ),
    "docs/product/pr_110_external_expansion_gate.md": (
        "external-expansion-gate/v1",
        "não habilita capacidades externas",
        "não emite grant",
    ),
}

_LIMITED_PATHS = (
    {
        "id": "public_browser",
        "schema": "public-browser-read/v1",
        "capability": "browser.navigate_public",
        "limit": "GET público planejado; sem browser autenticado, cookies, JS, formulários, download ou credenciais",
    },
    {
        "id": "mcp_local",
        "schema": "mcp-local-tool/v1",
        "capability": "mcp.local_echo_digest",
        "limit": "tool local não sensível por digest; sem upstream MCP amplo, shell, rede ou credenciais",
    },
    {
        "id": "n8n_local_plan",
        "schema": "n8n-local-plan/v1",
        "capability": "n8n.local_plan_digest",
        "limit": "plano local por digest; sem n8n instance, activation, webhook, credenciais ou workflow real",
    },
    {
        "id": "permission_ux",
        "schema": "permission-ux/v1",
        "capability": "permission.explain_chain",
        "limit": "explica a cadeia; não emite grant, não consome grant e não despacha adapter",
    },
)


@dataclass(frozen=True)
class GateCheck:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _read_text(repo: Path, relative: str) -> str | None:
    try:
        return (repo / relative).read_text(encoding="utf-8")
    except OSError:
        return None


def _check_doc_markers(repo: Path) -> list[GateCheck]:
    checks: list[GateCheck] = []
    for relative, markers in _REQUIRED_DOC_MARKERS.items():
        text = _read_text(repo, relative)
        if text is None:
            checks.append(GateCheck(f"doc:{relative}", "fail", "required external expansion document missing"))
            continue
        missing = [marker for marker in markers if marker not in text]
        checks.append(GateCheck(
            f"doc:{relative}",
            "fail" if missing else "ok",
            f"missing markers: {', '.join(missing)}" if missing else "required markers present",
        ))
    return checks


def _check_adapter_registry() -> tuple[GateCheck, list[dict[str, Any]]]:
    payload = collect_adapter_registry()
    adapters = list(payload.get("adapters", []))
    enabled: list[str] = []
    for adapter in adapters:
        adapter_id = str(adapter.get("id", "unknown"))
        for flag in _EXTERNAL_ENABLE_FLAGS:
            if bool(adapter.get(flag, False)):
                enabled.append(f"{adapter_id}.{flag}")
    if enabled:
        return GateCheck("runtime:adapter_registry_external_flags", "fail", ", ".join(enabled[:12])), adapters
    return GateCheck(
        "runtime:adapter_registry_external_flags",
        "ok",
        "adapter registry keeps external execution, credentials, publication and broad tools disabled",
    ), adapters


def _check_limited_runtime_paths() -> tuple[list[GateCheck], dict[str, Any]]:
    public_browser = collect_public_browser(url="https://example.com/", browser_action="plan")
    mcp_local = collect_mcp_local_tool(mcp_action="plan", channel="external-expansion-gate")
    n8n_local = collect_n8n_local_plan(n8n_action="plan", channel="external-expansion-gate")
    blocked_permission = collect_permission_ux(
        adapter_id="n8n",
        requested_capability="n8n.activate_workflow",
        actor="user",
        channel="workbench",
        domain="automation",
        action="ativar workflow n8n real",
        approval_intent=True,
        approved_by="external-expansion-gate",
        operation_scope="n8n-local-plan",
    )
    checks = [
        GateCheck(
            "runtime:public_browser_plan_only",
            "ok" if public_browser.get("browser_action") == "plan" and not public_browser.get("fetch_attempted") and not public_browser.get("network_calls") else "fail",
            "public browser plan does not fetch or use network",
        ),
        GateCheck(
            "runtime:mcp_local_no_upstream",
            "ok" if not mcp_local.get("local_tool_executed") and not mcp_local.get("executes_upstream_mcp_tools") else "fail",
            "mcp local plan does not execute local or upstream tools",
        ),
        GateCheck(
            "runtime:n8n_local_no_workflow",
            "ok" if not n8n_local.get("workflow_executed") and not n8n_local.get("workflow_activated") and not n8n_local.get("calls_n8n_instance") else "fail",
            "n8n local plan does not call n8n or execute workflow",
        ),
        GateCheck(
            "runtime:blocked_external_permission_ux",
            "ok" if not blocked_permission.get("effective", {}).get("effective_authorization") and not blocked_permission.get("execution", {}).get("adapter_executed") else "fail",
            "permission UX keeps n8n real activation non-effective and non-executing",
        ),
    ]
    evidence = {
        "public_browser": {
            "schema_version": public_browser.get("schema_version"),
            "overall": public_browser.get("overall"),
            "browser_action": public_browser.get("browser_action"),
            "fetch_attempted": bool(public_browser.get("fetch_attempted")),
            "network_calls": bool(public_browser.get("network_calls")),
            "credentialed_access": bool(public_browser.get("credentialed_access")),
        },
        "mcp_local": {
            "schema_version": mcp_local.get("schema_version"),
            "overall": mcp_local.get("overall"),
            "local_tool_executed": bool(mcp_local.get("local_tool_executed")),
            "executes_upstream_mcp_tools": bool(mcp_local.get("executes_upstream_mcp_tools")),
            "external_side_effects": bool(mcp_local.get("external_side_effects")),
        },
        "n8n_local_plan": {
            "schema_version": n8n_local.get("schema_version"),
            "overall": n8n_local.get("overall"),
            "workflow_executed": bool(n8n_local.get("workflow_executed")),
            "workflow_activated": bool(n8n_local.get("workflow_activated")),
            "calls_n8n_instance": bool(n8n_local.get("calls_n8n_instance")),
            "webhook_called": bool(n8n_local.get("webhook_called")),
        },
        "blocked_permission_ux": {
            "schema_version": blocked_permission.get("schema_version"),
            "decision": blocked_permission.get("decision", {}).get("outcome"),
            "effective_authorization": bool(blocked_permission.get("effective", {}).get("effective_authorization")),
            "adapter_executed": bool(blocked_permission.get("execution", {}).get("adapter_executed")),
        },
    }
    return checks, evidence


def collect_external_expansion_gate(*, repo: Path | None = None) -> dict[str, Any]:
    repo = (repo or Path.cwd()).resolve()
    checks = _check_doc_markers(repo)
    registry_check, adapters = _check_adapter_registry()
    checks.append(registry_check)
    runtime_checks, runtime_evidence = _check_limited_runtime_paths()
    checks.extend(runtime_checks)
    hard_fail = any(check.status == "fail" for check in checks)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "external-expansion-gate",
        "schema_version": _SCHEMA_VERSION,
        "overall": "blocked" if hard_fail else "ready",
        "decision": "blocked_by_missing_evidence" if hard_fail else "no_go_for_external_effects",
        "summary": "external expansion remains blocked; current evidence supports only narrow local/read-only paths",
        "domain": "external_capability_governance",
        "channel": "cli_gateway_workbench",
        "autonomy": "read_only_go_no_go",
        "capability": "external_expansion.go_no_go_check",
        "external_expansion_allowed": False,
        "external_capabilities_enabled": False,
        "publication_allowed": False,
        "human_publication_approval_required": True,
        "tag_or_release_created": False,
        "publishes_external_artifact": False,
        "blocked_external_capabilities": list(_BLOCKED_EXTERNAL_CAPABILITIES),
        "limited_current_paths": list(_LIMITED_PATHS),
        "adapter_count": len(adapters),
        "runtime_evidence": runtime_evidence,
        "required_before_go": [
            "spec própria por capacidade externa",
            "contenção do executor demonstrada por testes negativos",
            "capability exata com escopo mínimo e identidade verificada",
            "grant single-use quando houver efeito real",
            "aprovação humana explícita para conteúdo, destino, recurso e consequência",
            "matriz e documentação pública atualizadas sem overclaiming",
        ],
        "checks": [check.as_dict() for check in checks],
        "security": {
            "read_only": True,
            "modifies_files": False,
            "starts_server": False,
            "network_access": False,
            "calls_n8n_instance": False,
            "executes_tools": False,
            "dispatches_adapter": False,
            "issues_grants": False,
            "consumes_grants": False,
            "uses_credentials": False,
            "publishes_release": False,
            "sends_messages": False,
            "submits_forms": False,
            "grants_permissions": False,
            "external_side_effects": False,
            "prints_tokens": False,
        },
    }


def render_external_expansion_gate(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway external-expansion-gate: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        "external_expansion_allowed: false",
        "external_capabilities_enabled: false",
        "publication_allowed: false",
        "human_publication_approval_required: true",
        "read_only: true",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
    ]
    lines.append("blocked_capabilities:")
    for item in payload.get("blocked_external_capabilities", [])[:10]:
        lines.append(f"  - {item.get('capability')}: {item.get('reason')}")
    lines.append("checks:")
    for check in payload.get("checks", []):
        lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")
    return "\n".join(lines)
