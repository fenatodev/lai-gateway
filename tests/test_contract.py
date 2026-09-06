from __future__ import annotations

import copy
import unittest

from lai_gateway.contract import assert_no_secret_values, summarize_contract, validate_gateway_contract
from lai_gateway.errors import ConfigError

from .fixtures import CONTRACT


class ContractTest(unittest.TestCase):
    def test_validates_and_summarizes_v042_contract(self):
        payload = validate_gateway_contract(copy.deepcopy(CONTRACT))
        summary = summarize_contract(payload)
        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["product"], "lai harness")
        self.assertEqual(summary["version"], "0.4.2")
        self.assertGreaterEqual(summary["route_count"], 5)
        self.assertGreaterEqual(summary["forbidden_count"], 3)

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

    def test_rejects_secret_shaped_fields_but_allows_documented_auth_shape(self):
        payload = copy.deepcopy(CONTRACT)
        assert_no_secret_values(payload)
        payload["actual_api_key"] = "abc123"
        with self.assertRaisesRegex(ConfigError, "secret-shaped"):
            assert_no_secret_values(payload)


if __name__ == "__main__":
    unittest.main()
