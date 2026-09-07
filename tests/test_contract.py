from __future__ import annotations

import copy
import unittest

from lai_gateway.contract import assert_no_secret_values, summarize_contract, validate_gateway_contract
from lai_gateway.errors import ConfigError

from .fixtures import CONTRACT


class ContractTest(unittest.TestCase):
    def test_validates_and_summarizes_v045_contract(self):
        payload = validate_gateway_contract(copy.deepcopy(CONTRACT))
        summary = summarize_contract(payload)
        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["product"], "lai harness")
        self.assertEqual(summary["version"], "0.4.5")
        self.assertGreaterEqual(summary["route_count"], 12)
        self.assertGreaterEqual(summary["forbidden_count"], 3)
        routes = {(route["method"], route["path"]) for route in payload["routes"]}
        self.assertIn(("GET", "/v1/sessions?limit=N"), routes)
        self.assertIn(("POST", "/v1/sessions"), routes)
        self.assertIn(("GET", "/v1/sessions/{session_id}"), routes)
        self.assertIn(("DELETE", "/v1/sessions/{session_id}"), routes)
        self.assertIn(("GET", "/v1/runs?limit=N"), routes)
        self.assertIn(("POST", "/v1/runs"), routes)
        self.assertIn(("GET", "/v1/runs/{control_run_id}"), routes)

    def test_rejects_shell_or_direct_llama_contract_drift(self):
        payload = copy.deepcopy(CONTRACT)
        payload["capabilities"]["shell_execution"] = True
        with self.assertRaisesRegex(ConfigError, "shell"):
            validate_gateway_contract(payload)
        payload = copy.deepcopy(CONTRACT)
        payload["capabilities"]["direct_llama_proxy"] = True
        with self.assertRaisesRegex(ConfigError, "llama"):
            validate_gateway_contract(payload)

    def test_rejects_missing_required_routes_and_forbidden_boundaries(self):
        payload = copy.deepcopy(CONTRACT)
        payload["routes"] = [route for route in payload["routes"] if route["path"] != "/v1/runs"]
        with self.assertRaisesRegex(ConfigError, "missing required routes"):
            validate_gateway_contract(payload)
        payload = copy.deepcopy(CONTRACT)
        payload["forbidden_capabilities"].remove("generic_remote_shell")
        with self.assertRaisesRegex(ConfigError, "missing forbidden"):
            validate_gateway_contract(payload)


    def test_requires_run_routes_used_by_gateway(self):
        for path in (
            "/v1/runs?limit=N",
            "/v1/runs",
            "/v1/runs/{control_run_id}",
        ):
            payload = copy.deepcopy(CONTRACT)
            payload["routes"] = [route for route in payload["routes"] if route["path"] != path]
            with self.assertRaisesRegex(ConfigError, "missing required routes"):
                validate_gateway_contract(payload)

    def test_requires_session_routes_used_by_gateway(self):
        for path in (
            "/v1/sessions?limit=N",
            "/v1/sessions",
            "/v1/sessions/{session_id}",
        ):
            payload = copy.deepcopy(CONTRACT)
            payload["routes"] = [route for route in payload["routes"] if route["path"] != path]
            with self.assertRaisesRegex(ConfigError, "missing required routes"):
                validate_gateway_contract(payload)

    def test_requires_mcp_routes_and_capabilities(self):
        for path in ("/v1/mcp/status", "/v1/mcp/tools", "/v1/mcp/policy-check"):
            payload = copy.deepcopy(CONTRACT)
            payload["routes"] = [route for route in payload["routes"] if route["path"] != path]
            with self.assertRaisesRegex(ConfigError, "missing required routes"):
                validate_gateway_contract(payload)

        payload = copy.deepcopy(CONTRACT)
        payload["capabilities"]["mcp_broker_foundation"] = False
        with self.assertRaisesRegex(ConfigError, "MCP broker"):
            validate_gateway_contract(payload)

        payload = copy.deepcopy(CONTRACT)
        payload["capabilities"]["mcp_tool_execution"] = True
        with self.assertRaisesRegex(ConfigError, "MCP tool execution"):
            validate_gateway_contract(payload)

    def test_rejects_secret_shaped_fields_but_allows_documented_auth_shape(self):
        payload = copy.deepcopy(CONTRACT)
        assert_no_secret_values(payload)
        payload["actual_api_key"] = "abc123"
        with self.assertRaisesRegex(ConfigError, "secret-shaped"):
            assert_no_secret_values(payload)


if __name__ == "__main__":
    unittest.main()
