from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.tokens import check_gateway_access_token_file, create_gateway_access_token


class TokenTest(unittest.TestCase):
    def test_create_and_check_gateway_access_token_file_is_secret_free_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access-token"
            payload = create_gateway_access_token(path)
            self.assertEqual(payload["mode"], "0600")
            self.assertGreaterEqual(payload["token_length"], 32)
            self.assertNotIn("token", payload)
            checked = check_gateway_access_token_file(path)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["mode"], "0600")

    def test_rejects_too_permissive_gateway_access_token_file(self) -> None:
        if os.name != "posix":
            self.skipTest("posix permission check")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access-token"
            path.write_text("x" * 40, encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(Exception, "0600"):
                check_gateway_access_token_file(path)

    def test_cli_token_create_and_check_do_not_print_token_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access-token"
            created = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "token", "create", "--path", str(path), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            payload = json.loads(created.stdout)
            self.assertEqual(payload["mode"], "0600")
            self.assertFalse(payload["printed_token"])
            self.assertNotIn('"token":', created.stdout)
            real_token = path.read_text(encoding="utf-8").strip()
            self.assertNotIn(real_token, created.stdout)

            checked = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "token", "check", "--path", str(path), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertNotIn(real_token, checked.stdout)
            self.assertTrue(json.loads(checked.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
