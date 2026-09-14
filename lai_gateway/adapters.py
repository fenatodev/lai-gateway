from typing import Any

from . import __version__

_GOVERNED_ADAPTERS: tuple[dict[str, Any], ...] = (
    {
        "id": "mcp",
        "title": "MCP broker foundation",
        "kind": "protocol_adapter",
        "domain": "tools",
        "channels": ["gateway", "workbench"],
        "autonomy": "policy_checked_read_only",
        "entrypoints": [
            "/v1/harness/mcp/status",
            "/v1/harness/mcp/tools",
            "/v1/harness/mcp/policy-check",
        ],
        "requested_capabilities": ["mcp.status", "mcp.list_tools", "mcp.policy_check"],
        "granted_capabilities": [],
        "executes_tools": False,
        "grants_permissions": False,
        "requires_policy_check": True,
        "human_approval_required_for": ["mcp.call_tool", "credentialed_tool", "filesystem_write", "network_side_effect"],
        "status": "foundation_only",
        "purpose": "Inspect MCP broker metadata and classify tool calls without executing tools.",
    },
)


def governed_adapters() -> list[dict[str, Any]]:
    return [dict(adapter) for adapter in _GOVERNED_ADAPTERS]


def collect_adapter_registry(*, adapter_id: str | None = None) -> dict[str, Any]:
    adapters = governed_adapters()
    if adapter_id:
        adapters = [adapter for adapter in adapters if adapter["id"] == adapter_id]
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "adapter-registry",
        "overall": "ready" if adapters else "missing",
        "count": len(adapters),
        "adapters": adapters,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": any(adapter.get("executes_tools") for adapter in adapters),
        "security": {
            "prints_tokens": False,
            "grants_permissions": any(adapter.get("grants_permissions") for adapter in adapters),
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "tool_execution_enabled": any(adapter.get("executes_tools") for adapter in adapters),
        },
    }


def render_adapter_registry(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway adapter-registry: {payload['overall']}",
        f"version: {payload['version']}",
        f"count: {payload['count']}",
        "grants_permissions: false",
        "tool_execution_enabled: false",
    ]
    for adapter in payload.get("adapters", []):
        requested = ", ".join(adapter.get("requested_capabilities", [])) or "none"
        granted = ", ".join(adapter.get("granted_capabilities", [])) or "none"
        lines.append(
            f"- {adapter['id']}: kind={adapter['kind']} autonomy={adapter['autonomy']} requested={requested} granted={granted} executes_tools={adapter.get('executes_tools', False)}"
        )
    return "\n".join(lines)
