from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.config import GatewayConfig
from lai_gateway.telegram import (
    build_mobile_access_telegram_text,
    collect_telegram_preflight,
    discover_telegram_chats,
    notify_gateway_status,
    notify_mobile_access,
    send_telegram_message,
)


class _FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return None
    def read(self) -> bytes:
        return json.dumps({"ok": True, "result": {"message_id": 42}}).encode("utf-8")


class _FakeUpdatesResponse:
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return None
    def read(self) -> bytes:
        return json.dumps({
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "secret hello", "chat": {"id": 777, "type": "private", "username": "fenato"}}},
                {"update_id": 2, "message": {"text": "another secret", "chat": {"id": 777, "type": "private", "username": "fenato"}}},
                {"update_id": 3, "channel_post": {"text": "channel secret", "chat": {"id": -100, "type": "channel", "title": "Ops"}}},
            ],
        }).encode("utf-8")


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


    def test_discover_chat_requires_receive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token_file.write_text("123456789:abcdefghijklmnopqrstuvwxyz", encoding="utf-8")
            os.chmod(token_file, 0o600)
            with self.assertRaises(Exception):
                discover_telegram_chats(token_file=token_file, enable_receive=False)

    def test_discover_chat_uses_getupdates_and_redacts_text(self) -> None:
        captured = {}
        def opener(request, timeout=10):
            captured["url"] = request.full_url
            return _FakeUpdatesResponse()
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            payload = discover_telegram_chats(token_file=token_file, enable_receive=True, opener=opener)
            stdout = json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["operation"], "telegram-discover-chat")
            self.assertEqual(payload["candidate_count"], 2)
            self.assertIn("getUpdates", captured["url"])
            self.assertIn(token, captured["url"])
            self.assertNotIn(token, stdout)
            self.assertNotIn("secret hello", stdout)
            self.assertTrue(payload["security"]["message_text_redacted"])
            self.assertFalse(payload["security"]["webhook_exposed"])

    def test_cli_discover_chat_requires_explicit_receive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token_file.write_text("123456789:abcdefghijklmnopqrstuvwxyz", encoding="utf-8")
            os.chmod(token_file, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "discover-chat", "--token-file", str(token_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("123456789:abcdefghijklmnopqrstuvwxyz", result.stdout + result.stderr)

    def test_notify_mobile_access_sends_url_without_tokens(self) -> None:
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
            payload = notify_mobile_access(
                port=8787,
                bind="127.0.0.1",
                token_file=token_file,
                chat_id="123",
                enable_send=True,
                opener=opener,
            )
            stdout = json.dumps(payload, sort_keys=True)
            self.assertEqual(payload["operation"], "telegram-notify-mobile")
            self.assertTrue(payload["mobile_url_included"])
            self.assertFalse(payload["pair_token_included"])
            self.assertFalse(payload["harness_token_included"])
            self.assertIn("lai-gateway+mobile+access", captured["data"])
            self.assertNotIn("pair_token", captured["data"])
            self.assertNotIn(token, stdout)

    def test_mobile_access_text_is_bounded_and_secret_free(self) -> None:
        text = build_mobile_access_telegram_text(port=8787, bind="127.0.0.1")
        self.assertLessEqual(len(text), 4096)
        self.assertIn("lai-gateway mobile access", text)
        self.assertNotIn("pair_token", text)
        self.assertNotIn("harness", text.lower().replace("harness_control_token", ""))


    def test_notify_status_sends_doctor_summary_without_tokens(self) -> None:
        captured = {}
        def opener(request, timeout=10):
            captured["url"] = request.full_url
            captured["data"] = request.data.decode("utf-8")
            return _FakeResponse()
        with tempfile.TemporaryDirectory() as tmp:
            harness_token = Path(tmp) / "harness-token"
            harness_token.write_text("harness-secret-value", encoding="utf-8")
            os.chmod(harness_token, 0o600)
            telegram_token = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            telegram_token.write_text(token, encoding="utf-8")
            os.chmod(telegram_token, 0o600)
            config = GatewayConfig.from_env({
                "LAI_GATEWAY_TOKEN_FILE": str(harness_token),
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:1",
            })
            payload = notify_gateway_status(
                config=config,
                token_file=telegram_token,
                chat_id="123",
                enable_send=True,
                opener=opener,
            )
            stdout = json.dumps(payload, sort_keys=True)
            self.assertEqual(payload["operation"], "telegram-notify-status")
            self.assertTrue(payload["status_included"])
            self.assertFalse(payload["token_included"])
            self.assertIn("lai-gateway+status", captured["data"])
            self.assertNotIn("harness-secret-value", captured["data"])
            self.assertNotIn(token, stdout)


if __name__ == "__main__":
    unittest.main()
