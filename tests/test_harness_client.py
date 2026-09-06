from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.fake_harness as fake
from lai_gateway.config import GatewayConfig
from lai_gateway.errors import ConfigError, HarnessHTTPError
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
            self.assertEqual(client.get_session("s_test")["session"]["session_id"], "s_test")

    def test_fetches_and_creates_read_only_runs_with_bounded_body(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))

            listed = client.list_runs(limit=1)
            created = client.create_read_only_run(
                mode="plan",
                task="Summarize current state.",
                session_id="s_test",
            )
            fetched = client.get_run("cr_test")

            self.assertEqual(listed["runs"][0]["control_run_id"], "cr_test")
            self.assertEqual(created["run"]["control_run_id"], "cr_test")
            self.assertEqual(fetched["run"]["status"], "succeeded")
            self.assertEqual(fake.LAST_RUN_BODY, {
                "mode": "plan",
                "session_id": "s_test",
                "task": "Summarize current state.",
            })

    def test_rejects_write_modes_before_contacting_harness(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            with self.assertRaises(ConfigError):
                client.create_read_only_run(mode="implement", task="change files")

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
