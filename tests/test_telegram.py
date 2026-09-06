from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.telegram import collect_telegram_preflight, send_telegram_message


class _FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return None
    def read(self) -> bytes:
        return json.dumps({"ok": True, "result": {"message_id": 42}}).encode("utf-8")


class TelegramTest(unittest.TestCase):
    def test_cli_telegram_preflight_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "preflight", "--token-file", str(token_file), "--chat-id", "123", "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "telegram-preflight")
            self.assertFalse(payload["network_call"])
            self.assertNotIn(token, result.stdout)
            self.assertNotIn("Bearer", result.stdout)

    def test_preflight_is_secret_free_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token_file.write_text("123456789:abcdefghijklmnopqrstuvwxyz", encoding="utf-8")
            os.chmod(token_file, 0o600)
            payload = collect_telegram_preflight(token_file=token_file, chat_id="123", enable_send=False)
            stdout = json.dumps(payload, sort_keys=True)
            self.assertEqual(payload["overall"], "needs_config")
            self.assertFalse(payload["network_call"])
            self.assertFalse(payload["send_enabled"])
            self.assertNotIn("123456789:abcdefghijklmnopqrstuvwxyz", stdout)
            self.assertFalse(payload["security"]["webhook_exposed"])

    def test_send_message_requires_enable_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token_file.write_text("123456789:abcdefghijklmnopqrstuvwxyz", encoding="utf-8")
            os.chmod(token_file, 0o600)
            with self.assertRaises(Exception):
                send_telegram_message(text="hi", token_file=token_file, chat_id="123", enable_send=False)

    def test_send_message_uses_injected_opener_without_printing_token(self) -> None:
        captured = {}
        def opener(request, timeout=10):
            captured["url"] = request.full_url
            captured["data"] = request.data.decode("utf-8")
            return _FakeResponse()
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            payload = send_telegram_message(
                text="LAI ready",
                token_file=token_file,
                chat_id="123",
                enable_send=True,
                opener=opener,
            )
            stdout = json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["message_id"], 42)
            self.assertIn(token, captured["url"])
            self.assertNotIn(token, stdout)
            self.assertFalse(payload["webhook_exposed"])


if __name__ == "__main__":
    unittest.main()
