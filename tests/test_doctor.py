from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lai_gateway import __version__

from lai_gateway.config import GatewayConfig
from lai_gateway.doctor import collect_doctor, render_doctor

from .fake_harness import TOKEN, fake_harness


class DoctorTest(unittest.TestCase):
    def test_doctor_reports_ready_without_printing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)

            payload = collect_doctor(config)
            rendered = render_doctor(payload)

            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(payload["version"], __version__)
            self.assertIn("harness_status", {check["name"] for check in payload["checks"]})
            self.assertIn("gateway_contract", {check["name"] for check in payload["checks"]})
            self.assertNotIn(TOKEN, rendered)
            self.assertIn(str(token_file), rendered)

    def test_doctor_blocks_missing_token_before_harness_contact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "missing-token"
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)

            payload = collect_doctor(config)

            self.assertEqual(payload["overall"], "blocked")
            self.assertTrue(any(check["name"] == "token_file" and check["status"] == "fail" for check in payload["checks"]))
            self.assertFalse(any(check["name"] == "harness_status" for check in payload["checks"]))


if __name__ == "__main__":
    unittest.main()
