from typing import Any

from . import __version__

_BUILTIN_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "id": "grill",
        "title": "Grill crítico",
        "domain": "review",
        "channels": ["chat", "vscode", "workbench"],
        "autonomy": "advisory",
        "requested_capabilities": [],
        "grants_permissions": False,
        "purpose": "Criticar premissas, riscos e inconsistências sem executar ações.",
    },
    {
        "id": "architect",
        "title": "Arquiteto LAI",
        "domain": "architecture",
        "channels": ["chat", "vscode", "workbench"],
        "autonomy": "advisory",
        "requested_capabilities": ["read_repo", "inspect_contracts"],
        "grants_permissions": False,
        "purpose": "Revisar contratos, fronteiras de core/adapters e decisões técnicas.",
    },
    {
        "id": "spec",
        "title": "Spec curta",
        "domain": "planning",
        "channels": ["chat", "vscode", "workbench"],
        "autonomy": "advisory",
        "requested_capabilities": ["write_docs"],
        "grants_permissions": False,
        "purpose": "Transformar intenção em especificação pequena antes de mudança relevante.",
    },
    {
        "id": "frontend",
        "title": "Frontend workbench",
        "domain": "ui",
        "channels": ["vscode", "workbench"],
        "autonomy": "sandboxed_work",
        "requested_capabilities": ["read_repo", "write_sandbox", "run_checks"],
        "grants_permissions": False,
        "purpose": "Melhorar UI local sem publicar nem aplicar fora do lifecycle aprovado.",
    },
    {
        "id": "dev",
        "title": "Dev controlado",
        "domain": "engineering",
        "channels": ["vscode", "workbench"],
        "autonomy": "sandboxed_work",
        "requested_capabilities": ["read_repo", "write_sandbox", "run_checks"],
        "grants_permissions": False,
        "purpose": "Executar desenvolvimento assistido somente via harness/review/apply.",
    },
    {
        "id": "security",
        "title": "Segurança e permissões",
        "domain": "security",
        "channels": ["chat", "vscode", "workbench"],
        "autonomy": "advisory",
        "requested_capabilities": ["read_repo", "inspect_contracts"],
        "grants_permissions": False,
        "purpose": "Revisar ameaças, segredos, sandbox, approval e boundaries.",
    },
    {
        "id": "scout",
        "title": "Scout técnico",
        "domain": "research",
        "channels": ["chat", "workbench"],
        "autonomy": "approval_required_external",
        "requested_capabilities": ["network_research"],
        "grants_permissions": False,
        "purpose": "Preparar pesquisa técnica; acesso externo continua sujeito a aprovação/policy.",
    },
)


def builtin_skills() -> list[dict[str, Any]]:
    return [dict(skill) for skill in _BUILTIN_SKILLS]


def collect_skills_registry(*, skill_id: str | None = None) -> dict[str, Any]:
    skills = builtin_skills()
    if skill_id:
        skills = [skill for skill in skills if skill["id"] == skill_id]
    overall = "ready" if skills else "missing"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "skills-registry",
        "overall": overall,
        "count": len(skills),
        "skills": skills,
        "starts_server": False,
        "modifies_files": False,
        "executes_adapters": False,
        "security": {
            "prints_tokens": False,
            "grants_permissions": any(skill.get("grants_permissions") for skill in skills),
            "executes_adapters": False,
            "channels_elevate_permissions": False,
        },
    }


def render_skills_registry(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway skills-registry: {payload['overall']}",
        f"version: {payload['version']}",
        f"count: {payload['count']}",
        "grants_permissions: false",
    ]
    for skill in payload.get("skills", []):
        capabilities = ", ".join(skill.get("requested_capabilities", [])) or "none"
        channels = ", ".join(skill.get("channels", [])) or "none"
        lines.append(
            f"- {skill['id']}: domain={skill['domain']} autonomy={skill['autonomy']} channels={channels} requested={capabilities}"
        )
    return "\n".join(lines)
