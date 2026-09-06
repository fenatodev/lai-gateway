from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .fake_harness import TOKEN, fake_harness


class CliTest(unittest.TestCase):
    def test_cli_contract_fetches_summary_without_printing_token(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "contract"],
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
                env=env,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["version"], "0.4.2")
            self.assertNotIn(TOKEN, result.stdout)
            self.assertEqual(result.stderr, "")

    def test_cli_config_prints_path_not_token_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "config"],
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
                env=env,
            )
            self.assertIn(str(token_file), result.stdout)
            self.assertNotIn(TOKEN, result.stdout)


if __name__ == "__main__":
    unittest.main()
