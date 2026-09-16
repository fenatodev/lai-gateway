from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .doctor import collect_doctor
from .document_workbench import collect_document_workbench
from .errors import ConfigError, GatewayError
from .model import collect_model_status

_SCHEMA_VERSION = "onboarding-next-steps/v1"


def collect_onboarding_status(
    *,
    config: GatewayConfig | None = None,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return a sanitized onboarding map for the Workbench."""
    config_error: str | None = None
    try:
        resolved_config = config or GatewayConfig.from_env()
    except (ConfigError, GatewayError) as exc:
        resolved_config = None
        config_error = _safe_detail(str(exc))
    doctor = collect_doctor(resolved_config) if resolved_config is not None else {
        "overall": "blocked",
        "checks": [{"name": "config", "status": "fail", "detail": config_error or "gateway config unavailable"}],
    }
    model = collect_model_status(probe_openai=False)
    document = _document_probe(workspace_root)
    cards = [
        _token_card(doctor),
        _harness_card(doctor),
        _model_card(model),
        _document_card(document, workspace_root),
        _safety_card(),
    ]
    statuses = {card["status"] for card in cards}
    overall = "blocked" if "blocked" in statuses else "warn" if "warn" in statuses else "ready"
    next_steps = _dedupe([step for card in cards for step in card.get("next_steps", [])])
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "onboarding",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "summary": _summary(overall, next_steps),
        "cards": cards,
        "next_steps": next_steps,
        "source_statuses": {
            "doctor": doctor.get("overall", "unknown"),
            "model": model.get("overall", "unknown"),
            "document": document.get("overall", "unknown"),
        },
        "limits": {
            "read_only": True,
            "document_workspace_required": True,
            "model_probe_network_call": False,
            "max_visible_steps": 8,
        },
        "security": {
            "prints_tokens": False,
            "prints_paths": False,
            "prints_harness_token": False,
            "prints_gateway_access_token": False,
            "prints_pairing_secret": False,
            "prints_document_content": False,
            "starts_server": False,
            "modifies_files": False,
            "network_access": False,
            "executes_tools": False,
            "grants_authority": False,
            "grants_permission": False,
            "external_side_effects": False,
        },
    }


def render_onboarding_status(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway onboarding: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        "schema: onboarding-next-steps/v1",
        "read_only: true",
        "prints_tokens: false",
        "prints_paths: false",
        "starts_server: false",
        "modifies_files: false",
        "executes_tools: false",
    ]
    for card in payload.get("cards", []):
        lines.append(f"{card.get('area', 'unknown')}: {card.get('status', 'unknown')} - {card.get('summary', '')}")
        for step in card.get("next_steps", [])[:3]:
            lines.append(f"  next: {step}")
    return "\n".join(lines)


def _document_probe(workspace_root: str | Path | None) -> dict[str, Any]:
    if not workspace_root:
        return {
            "operation": "document-workbench",
            "overall": "warn",
            "workbench": {"status": "warn", "candidate_count": 0, "reason": "workspace not selected"},
            "security": {"prints_document_content": False, "external_side_effects": False},
        }
    return collect_document_workbench(workspace_root=workspace_root, max_results=10)


def _token_card(doctor: dict[str, Any]) -> dict[str, Any]:
    checks = _checks_by_name(doctor)
    token_status = checks.get("token_file", "missing")
    access_status = checks.get("access_token_file", "ok")
    if token_status == "fail":
        return _card(
            "token",
            "blocked",
            "Token de controle ausente ou inválido; o Harness não deve ser chamado até corrigir.",
            ["Configure LAI_GATEWAY_TOKEN_FILE para um arquivo 0600 com um único token."],
        )
    if access_status == "fail":
        return _card(
            "token",
            "blocked",
            "Gateway privado exige token de acesso local válido antes da UI mobile.",
            ["Recrie o token de acesso local com o comando de pareamento do Gateway."],
        )
    if token_status == "ok":
        return _card("token", "ready", "Token de controle presente; valor não é exibido.", [])
    return _card("token", "warn", "Estado do token ainda não foi confirmado.", ["Rode o diagnóstico de saúde do Workbench."])


def _harness_card(doctor: dict[str, Any]) -> dict[str, Any]:
    checks = _checks_by_name(doctor)
    if checks.get("harness_status") == "fail":
        return _card(
            "harness",
            "blocked",
            "Harness local não respondeu ao diagnóstico.",
            ["Inicie ou valide o Harness local antes de usar runs assistidos."],
        )
    if checks.get("harness_readiness") in {"fail", "warn"}:
        return _card(
            "harness",
            "warn",
            "Harness respondeu, mas a prontidão ainda não está verde.",
            ["Abra Saúde ou Status e corrija a prontidão do Harness antes de Trabalhar/Aplicar."],
        )
    if checks.get("harness_status") == "ok":
        return _card("harness", "ready", "Harness local respondeu e está apto para diagnóstico controlado.", [])
    return _card("harness", "warn", "Harness ainda não foi verificado nesta sessão.", ["Atualize Saúde no Workbench."])


def _model_card(model: dict[str, Any]) -> dict[str, Any]:
    config = model.get("model_config") if isinstance(model.get("model_config"), dict) else {}
    if not config.get("configured"):
        return _card(
            "modelo",
            "warn",
            "Modelo local ainda não está configurado; conversa direta usará fallback explícito.",
            ["Configure LAI_GATEWAY_MODEL_BASE_URL e LAI_GATEWAY_MODEL_NAME para um endpoint local/privado."],
        )
    if model.get("overall") == "ready":
        return _card("modelo", "ready", "Modelo local configurado; use Status do modelo para probe explícito.", [])
    return _card(
        "modelo",
        "warn",
        "Configuração de modelo existe, mas precisa de validação local explícita.",
        ["Use Status do modelo; nenhum fallback em nuvem será usado."],
    )


def _document_card(document: dict[str, Any], workspace_root: str | Path | None) -> dict[str, Any]:
    if not workspace_root:
        return _card(
            "documento",
            "warn",
            "Workspace de documento não selecionado; nenhuma leitura será feita automaticamente.",
            ["Informe um workspace explícito e liste apenas .txt, .md ou .json permitidos."],
        )
    workbench = document.get("workbench") if isinstance(document.get("workbench"), dict) else {}
    if document.get("overall") == "ready":
        return _card(
            "documento",
            "ready",
            f"Documento local restrito pronto; candidatos={workbench.get('candidate_count', 0)}.",
            [],
        )
    return _card(
        "documento",
        "blocked",
        "Workspace ou seleção de documento foi bloqueada pelas restrições locais.",
        ["Use caminho dentro do escopo do repo, sem symlink, sem PDF/OCR/Office e sem varredura de HOME."],
    )


def _safety_card() -> dict[str, Any]:
    return _card(
        "segurança",
        "ready",
        "Onboarding é diagnóstico read-only; conteúdo recuperado não concede autorização.",
        [],
    )


def _card(area: str, status: str, summary: str, next_steps: list[str]) -> dict[str, Any]:
    return {
        "area": area,
        "status": status,
        "summary": summary,
        "next_steps": next_steps,
        "prints_tokens": False,
        "prints_paths": False,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "grants_authority": False,
        "grants_permission": False,
        "external_side_effects": False,
    }


def _checks_by_name(doctor: dict[str, Any]) -> dict[str, str]:
    return {str(check.get("name")): str(check.get("status")) for check in doctor.get("checks", []) if isinstance(check, dict)}


def _summary(overall: str, next_steps: list[str]) -> str:
    if overall == "ready":
        return "Onboarding pronto; próximos passos críticos ausentes."
    return f"Onboarding {overall}; {len(next_steps)} próximo(s) passo(s) sanitizado(s)."


def _safe_detail(value: str) -> str:
    lowered = value.lower()
    if "token" in lowered:
        return "gateway token configuration is invalid"
    if "path" in lowered or "/" in value or "\\" in value:
        return "gateway configuration path is invalid"
    return value[:120]


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out[:8]
