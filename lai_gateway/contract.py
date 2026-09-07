from __future__ import annotations

from typing import Any

from .errors import ConfigError

REQUIRED_FORBIDDEN = {
    "generic_remote_shell",
    "direct_source_checkout_write",
    "control_token_or_model_api_key_disclosure",
}
REQUIRED_ROUTES = {
    ("GET", "/v1/gateway-contract"),
    ("GET", "/v1/status"),
    ("GET", "/v1/readiness"),
    ("GET", "/v1/sessions?limit=N"),
    ("POST", "/v1/sessions"),
    ("GET", "/v1/sessions/{session_id}"),
    ("DELETE", "/v1/sessions/{session_id}"),
    ("GET", "/v1/mcp/status"),
    ("GET", "/v1/mcp/tools"),
    ("POST", "/v1/mcp/policy-check"),
    ("GET", "/v1/runs?limit=N"),
    ("POST", "/v1/runs"),
    ("GET", "/v1/runs/{control_run_id}"),
    ("GET", "/v1/runs/{control_run_id}/events"),
}
SECRET_FIELD_TERMS = ("secret", "api_key", "password", "authorization")
ALLOWED_DOCUMENTATION_FIELDS = {"auth", "token_handling"}


def validate_gateway_contract(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ConfigError("unsupported gateway contract schema_version")
    if payload.get("product") != "lai harness":
        raise ConfigError("gateway contract product mismatch")
    if not isinstance(payload.get("version"), str) or not payload["version"]:
        raise ConfigError("gateway contract version is missing")
    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ConfigError("gateway contract routes must be a non-empty list")
    route_pairs = set()
    for route in routes:
        if not isinstance(route, dict):
            raise ConfigError("gateway contract route must be an object")
        method = route.get("method")
        path = route.get("path")
        if not isinstance(method, str) or not isinstance(path, str):
            raise ConfigError("gateway contract route must include method and path")
        if route.get("auth_required") is not True:
            raise ConfigError("every harness route exposed to the gateway must require auth")
        route_pairs.add((method, path))
    missing = sorted(REQUIRED_ROUTES - route_pairs)
    if missing:
        raise ConfigError(f"gateway contract missing required routes: {missing}")

    forbidden = payload.get("forbidden_capabilities")
    if not isinstance(forbidden, list):
        raise ConfigError("gateway contract forbidden_capabilities must be a list")
    missing_forbidden = sorted(REQUIRED_FORBIDDEN - set(forbidden))
    if missing_forbidden:
        raise ConfigError(f"gateway contract missing forbidden capabilities: {missing_forbidden}")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ConfigError("gateway contract capabilities must be an object")
    if capabilities.get("shell_execution") is not False:
        raise ConfigError("gateway contract must deny shell execution")
    if capabilities.get("direct_llama_proxy") is not False:
        raise ConfigError("gateway contract must deny direct llama proxy exposure")
    if capabilities.get("mcp_broker_foundation") is not True:
        raise ConfigError("gateway contract must expose the non-executing MCP broker foundation")
    if capabilities.get("mcp_tool_execution") is not False:
        raise ConfigError("gateway contract must deny MCP tool execution")
    return payload


def summarize_contract(payload: dict[str, Any]) -> dict[str, Any]:
    validate_gateway_contract(payload)
    return {
        "schema_version": payload["schema_version"],
        "product": payload["product"],
        "version": payload["version"],
        "route_count": len(payload["routes"]),
        "run_modes": payload.get("run_modes", {}),
        "limits": payload.get("limits", {}),
        "forbidden_count": len(payload.get("forbidden_capabilities", [])),
    }


def assert_no_secret_values(payload: dict[str, Any]) -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                lowered = str(key).lower()
                if any(term in lowered for term in SECRET_FIELD_TERMS) and key not in ALLOWED_DOCUMENTATION_FIELDS:
                    raise ConfigError(f"secret-shaped field is not allowed in contract: {path}.{key}")
                walk(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")
    walk(payload, "$")
