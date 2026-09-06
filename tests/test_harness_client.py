from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lai_gateway.config import GatewayConfig
from lai_gateway.errors import HarnessHTTPError
from lai_gateway.harness_client import HarnessClient

from .fake_harness import TOKEN, fake_harness


class HarnessClientTest(unittest.TestCase):
    def test_fetches_contract_status_readiness_and_sessions_with_bearer_auth(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            contract = client.gateway_contract()
            self.assertEqual(contract["version"], "0.4.2")
            self.assertEqual(client.status()["product"], "lai harness")
            self.assertEqual(client.readiness()["overall"], "ready")
            self.assertEqual(client.list_sessions()["sessions"][0]["session_id"], "s_test")
            self.assertEqual(client.create_session()["session"]["session_id"], "s_test")
            self.assertEqual(client.get_session("s_test")["session"]["turns"], [])

    def test_wrong_token_returns_bounded_harness_http_error(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text("wrong", encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            with self.assertRaises(HarnessHTTPError) as caught:
                client.status()
            self.assertEqual(caught.exception.status, 401)


if __name__ == "__main__":
    unittest.main()
