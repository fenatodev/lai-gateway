from __future__ import annotations

import re
import unicodedata
from typing import Any

from . import __version__
from .workbench_local_operator import WORKBENCH_LOCAL_OPERATOR_PROFILES


_SCHEMA_VERSION = "governed-conversational-routing/v1"

_MAX_MESSAGE_CHARS = 4_000
_MAX_HISTORY_MESSAGES = 16
_MAX_HISTORY_CHARS = 24_000

_AMBIGUOUS = {
    "ok",
    "sim",
    "yes",
    "vai",
    "pode",
    "isso",
    "continue",
    "continua",
    "prossiga",
    "proximo",
    "next",
    "faz isso",
    "faca isso",
}

_GREEN_PROFILE_PHRASES: dict[str, tuple[str, ...]] = {
    "status": (
        "git status",
        "status do repo",
        "status do repositorio",
        "estado do repo",
        "estado do repositorio",
        "repository status",
    ),
    "diff-check": (
        "git diff --check",
        "diff check",
        "validar o diff",
        "verificar o diff",
        "check the diff",
    ),
    "diff-stat": (
        "git diff --stat",
        "diff stat",
        "resumo do diff",
        "estatistica do diff",
        "diff summary",
    ),
    "compile": (
        "compileall",
        "compilar o projeto",
        "compile o projeto",
        "compile the project",
    ),
    "gate-tests": (
        "gate tests",
        "testes dos gates",
        "testes de gate",
        "review approval executor tests",
    ),
    "full-check": (
        "make check",
        "full check",
        "suite completa de checks",
        "todos os checks",
        "run all checks",
    ),
}

_SENSITIVE_PATTERNS = (
    r"^\s*sudo\b",
    r"\b(instale|instalar|install)\b.*\b(software|pacote|package|docker|podman|snap|apt|pip)\b",
    r"\b(remova|remover|remove|uninstall)\b.*\b(software|pacote|package)\b",
    r"\b(use|usar|utilize|utilizar)\b.*\b(token|credencial|credential|password|senha|api key)\b",
    r"\b(browser autenticado|authenticated browser|login com credencial|login with credential)\b",
    r"\b(envie|enviar|send)\b.*\b(email|telegram|slack|mensagem|message)\b",
    r"\b(publique|publicar|publish|release|deploy)\b",
    r"\b(submeta|submit|candidatura|application form|formulario|formulário)\b",
    r"\b(compre|comprar|buy|purchase)\b",
    r"\bmerge\b.*\bmain\b",
    r"\bgit push\b.*\bmain\b",
    r"^\s*(chmod|chown)\b",
    r"^\s*rm\s+-rf\b",
)

_UNSUPPORTED_PATTERNS = (
    r"\bwake word\b",
    r"\bcaptura de microfone\b",
    r"\bmicrophone capture\b",
    r"\bvoz operacional\b",
    r"\boperational voice\b",
    r"\bocr completo\b",
    r"\bfull ocr\b",
    r"\bmcp amplo\b",
    r"\bbroad mcp\b",
    r"\bativar n8n\b",
    r"\bactivate n8n\b",
    r"\bexecutar workflow n8n\b",
    r"\brun n8n workflow\b",
)

_SHELL_LIKE_PATTERNS = (
    r"&&",
    r"\|\|",
    r"`[^`]+`",
    r"\$\(",
    r"^\s*(bash|sh|zsh)\s+-c\b",
    r"^\s*rm\s+-",
    r"^\s*curl\b",
    r"^\s*wget\b",
)

_WORK_PATTERNS = (
    r"\bimplementar\b",
    r"\bimplemente\b",
    r"\bimplement\b",
    r"\bimplementation\b",
    r"\beditar\b",
    r"\bedite\b",
    r"\bedit\b",
    r"\balterar\b",
    r"\baltere\b",
    r"\bmodify\b",
    r"\bmodificar\b",
    r"\brefatorar\b",
    r"\brefactor\b",
    r"\bcorrigir\b",
    r"\bcorrija\b",
    r"\bfix\b",
    r"\bcriar arquivo\b",
    r"\bcreate file\b",
    r"\bescrever teste\b",
    r"\bwrite test\b",
    r"\bdesenvolver\b",
    r"\bdevelop\b",
    r"\bcodificar\b",
    r"\bcode change\b",
    r"\bmudar codigo\b",
    r"\bchange code\b",
)


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return " ".join(value.lower().split())


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _history_metadata(
    history: object,
) -> tuple[bool, int, int, str | None]:
    if history in (None, ()):
        return True, 0, 0, None

    if not isinstance(history, (tuple, list)):
        return False, 0, 0, "history must be a tuple or list"

    if len(history) > _MAX_HISTORY_MESSAGES:
        return False, len(history), 0, "history exceeds message limit"

    total_chars = 0
    expected_role = "user"

    for item in history:
        if not isinstance(item, dict):
            return False, len(history), total_chars, "history item must be an object"

        if set(item) != {"role", "content"}:
            return False, len(history), total_chars, "history item keys are invalid"

        role = item.get("role")
        content = item.get("content")

        if role != expected_role:
            return False, len(history), total_chars, "history roles must alternate"

        if not isinstance(content, str) or not content.strip():
            return False, len(history), total_chars, "history content is invalid"

        total_chars += len(content)

        if total_chars > _MAX_HISTORY_CHARS:
            return False, len(history), total_chars, "history exceeds character limit"

        expected_role = "assistant" if expected_role == "user" else "user"

    if len(history) % 2 != 0:
        return False, len(history), total_chars, "history must contain complete exchanges"

    return True, len(history), total_chars, None


def _result(
    *,
    route: str,
    domain: str,
    channel: str,
    autonomy: str,
    capability: str,
    reason_code: str,
    message_chars: int,
    history_message_count: int,
    history_chars: int,
    requires_explicit_transition: bool = False,
    requires_approval: bool = False,
    local_operator_profile: str | None = None,
) -> dict[str, Any]:
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "governed-conversational-routing",
        "schema_version": _SCHEMA_VERSION,
        "route": route,
        "domain": domain,
        "channel": channel,
        "autonomy": autonomy,
        "capability": capability,
        "reason_code": reason_code,
        "requires_explicit_transition": requires_explicit_transition,
        "requires_approval": requires_approval,
        "creates_harness_run": False,
        "grants_authority": False,
        "local_operator_profile": local_operator_profile,
        "input": {
            "message_chars": message_chars,
            "history_message_count": history_message_count,
            "history_chars": history_chars,
            "history_used_for_authorization": False,
        },
        "security": {
            "read_only": True,
            "executes_commands": False,
            "calls_harness": False,
            "calls_local_operator": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "issues_grants": False,
            "consumes_grants": False,
            "filesystem_write": False,
            "external_side_effects": False,
            "history_grants_authority": False,
            "model_output_grants_authority": False,
            "skill_grants_authority": False,
            "adapter_grants_authority": False,
            "channel_grants_authority": False,
        },
    }


def collect_governed_conversational_route(
    message: str,
    *,
    channel: str = "workbench",
    conversation_history: object = (),
) -> dict[str, Any]:
    channel_value = (
        _normalize_text(channel)
        if isinstance(channel, str) and channel.strip()
        else "unknown"
    )[:64]

    if not isinstance(message, str):
        return _result(
            route="blocked",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="none",
            reason_code="invalid_message_type",
            message_chars=0,
            history_message_count=0,
            history_chars=0,
        )

    message_chars = len(message)

    history_ok, history_count, history_chars, history_error = _history_metadata(
        conversation_history
    )

    if not history_ok:
        return _result(
            route="blocked",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="none",
            reason_code="invalid_history",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
        )

    if message_chars > _MAX_MESSAGE_CHARS:
        return _result(
            route="blocked",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="none",
            reason_code="message_too_large",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
        )

    normalized = _normalize_text(message)

    if not normalized or normalized in _AMBIGUOUS:
        return _result(
            route="clarify",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="none",
            reason_code="ambiguous_request",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
        )

    if _matches_any(normalized, _SENSITIVE_PATTERNS):
        return _result(
            route="approval_required",
            domain="governed-action",
            channel=channel_value,
            autonomy="approval-required",
            capability="approval.boundary",
            reason_code="sensitive_effect_requires_approval",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
            requires_approval=True,
        )

    if _matches_any(normalized, _UNSUPPORTED_PATTERNS):
        return _result(
            route="blocked",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="unsupported",
            reason_code="unsupported_capability",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
        )

    for profile, phrases in _GREEN_PROFILE_PHRASES.items():
        if profile not in WORKBENCH_LOCAL_OPERATOR_PROFILES:
            continue

        if any(phrase in normalized for phrase in phrases):
            return _result(
                route="local_green_candidate",
                domain="project-operations",
                channel=channel_value,
                autonomy="green",
                capability=f"local.operator.{profile}",
                reason_code="fixed_green_profile_match",
                message_chars=message_chars,
                history_message_count=history_count,
                history_chars=history_chars,
                local_operator_profile=profile,
            )

    if _matches_any(normalized, _SHELL_LIKE_PATTERNS):
        return _result(
            route="blocked",
            domain="routing",
            channel=channel_value,
            autonomy="none",
            capability="none",
            reason_code="arbitrary_shell_not_routable",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
        )

    if _matches_any(normalized, _WORK_PATTERNS):
        return _result(
            route="work_candidate",
            domain="project-development",
            channel=channel_value,
            autonomy="explicit-work-required",
            capability="development.work",
            reason_code="development_intent",
            message_chars=message_chars,
            history_message_count=history_count,
            history_chars=history_chars,
            requires_explicit_transition=True,
        )

    return _result(
        route="conversation",
        domain="conversation",
        channel=channel_value,
        autonomy="observe",
        capability="conversation.direct",
        reason_code="ordinary_conversation",
        message_chars=message_chars,
        history_message_count=history_count,
        history_chars=history_chars,
    )
