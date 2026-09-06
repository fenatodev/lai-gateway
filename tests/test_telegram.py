from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from urllib.error import HTTPError
from pathlib import Path

from lai_gateway.config import GatewayConfig
from lai_gateway.telegram import (
    build_mobile_access_telegram_text,
    collect_telegram_preflight,
    discover_telegram_chats,
    get_telegram_bot_info,
    inspect_telegram_chat_file,
    notify_gateway_status,
    notify_mobile_access,
    send_telegram_message,
    write_telegram_chat_file,
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


    def test_send_message_http_400_surfaces_safe_chat_not_found_hint(self) -> None:
        def opener(request, timeout=10):
            body = json.dumps({
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: chat not found",
            }).encode("utf-8")
            raise HTTPError(request.full_url, 400, "Bad Request", {}, BytesIO(body))
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            with self.assertRaises(Exception) as caught:
                send_telegram_message(
                    text="LAI ready",
                    token_file=token_file,
                    chat_id="123456789",
                    enable_send=True,
                    opener=opener,
                )
            message = str(caught.exception)
            self.assertIn("HTTP 400: Bad Request: chat not found", message)
            self.assertIn("telegram discover-chat", message)
            self.assertNotIn(token, message)
            self.assertNotIn("LAI ready", message)

    def test_send_message_http_error_redacts_token_shaped_description(self) -> None:
        def opener(request, timeout=10):
            body = json.dumps({
                "ok": False,
                "error_code": 400,
                "description": "bad 123456789:abcdefghijklmnopqrstuvwxyz value",
            }).encode("utf-8")
            raise HTTPError(request.full_url, 400, "Bad Request", {}, BytesIO(body))
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            with self.assertRaises(Exception) as caught:
                send_telegram_message(
                    text="hi",
                    token_file=token_file,
                    chat_id="123",
                    enable_send=True,
                    opener=opener,
                )
            message = str(caught.exception)
            self.assertIn("[redacted-token]", message)
            self.assertNotIn(token, message)

    def test_bot_info_returns_public_identity_without_token_or_messages(self) -> None:
        captured = {}
        class FakeGetMeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return None
            def read(self) -> bytes:
                return json.dumps({
                    "ok": True,
                    "result": {
                        "id": 8676089899,
                        "is_bot": True,
                        "first_name": "Amiga",
                        "username": "fenatobot",
                    },
                }).encode("utf-8")
        def opener(request, timeout=10):
            captured["url"] = request.full_url
            return FakeGetMeResponse()
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            payload = get_telegram_bot_info(token_file=token_file, opener=opener)
            stdout = json.dumps(payload, sort_keys=True)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["operation"], "telegram-bot-info")
            self.assertEqual(payload["username"], "fenatobot")
            self.assertEqual(payload["bot_id"], 8676089899)
            self.assertIn("getMe", captured["url"])
            self.assertNotIn(token, stdout)
            self.assertFalse(payload["security"]["message_text_read"])
            self.assertFalse(payload["security"]["webhook_exposed"])

    def test_chat_set_and_check_persist_0600_without_printing_chat_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chat_file = Path(tmp) / "telegram-chat-id"
            chat_id = "8560950373"
            set_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "telegram",
                    "chat-set",
                    "--chat-file",
                    str(chat_file),
                    "--chat-id",
                    chat_id,
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            set_payload = json.loads(set_result.stdout)
            self.assertTrue(set_payload["ok"])
            self.assertEqual(set_payload["operation"], "telegram-chat-set")
            self.assertEqual(oct(chat_file.stat().st_mode & 0o777), "0o600")
            self.assertEqual(chat_file.read_text(encoding="utf-8"), chat_id + "\n")
            self.assertNotIn(chat_id, set_result.stdout + set_result.stderr)
            check_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "telegram",
                    "chat-check",
                    "--chat-file",
                    str(chat_file),
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            check_payload = json.loads(check_result.stdout)
            self.assertEqual(check_payload["status"], "ready")
            self.assertFalse(check_payload["chat_id_printed"])
            self.assertNotIn(chat_id, check_result.stdout + check_result.stderr)

    def test_preflight_and_send_can_use_persisted_chat_file(self) -> None:
        captured = {}
        def opener(request, timeout=10):
            captured["data"] = request.data.decode("utf-8")
            return _FakeResponse()
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            chat_file = Path(tmp) / "telegram-chat-id"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            chat_id = "8560950373"
            token_file.write_text(token, encoding="utf-8")
            os.chmod(token_file, 0o600)
            write_telegram_chat_file(chat_id=chat_id, chat_file=chat_file)
            previous = os.environ.pop("LAI_GATEWAY_TELEGRAM_CHAT_ID", None)
            try:
                preflight = collect_telegram_preflight(
                    token_file=token_file,
                    chat_file=chat_file,
                    enable_send=True,
                )
                self.assertEqual(preflight["overall"], "ready")
                self.assertEqual(preflight["chat_id_source"], "file")
                self.assertNotIn(chat_id, json.dumps(preflight, sort_keys=True))
                payload = send_telegram_message(
                    text="LAI ready",
                    token_file=token_file,
                    chat_file=chat_file,
                    enable_send=True,
                    opener=opener,
                )
            finally:
                if previous is not None:
                    os.environ["LAI_GATEWAY_TELEGRAM_CHAT_ID"] = previous
            self.assertTrue(payload["ok"])
            self.assertIn("chat_id=8560950373", captured["data"])

    def test_chat_set_rejects_non_numeric_or_zero_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chat_file = Path(tmp) / "telegram-chat-id"
            for bad in ("<chat_id>", "0", "-0", "abc"):
                with self.subTest(bad=bad):
                    with self.assertRaises(Exception):
                        write_telegram_chat_file(chat_id=bad, chat_file=chat_file, force=True)

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

    def test_mobile_access_text_accepts_candidate_ip_without_tokens(self) -> None:
        text = build_mobile_access_telegram_text(port=8787, bind="127.0.0.1", candidate_ip="172.29.193.62")
        self.assertLessEqual(len(text), 4096)
        self.assertIn("bridge_target: 172.29.193.62", text)
        self.assertNotIn("pair_token", text)
        self.assertNotIn("Bearer", text)


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


    def test_token_check_reports_repairability_without_printing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text("123456789:\nabcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
            os.chmod(token_file, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "token-check", "--token-file", str(token_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["operation"], "telegram-token-check")
            self.assertTrue(payload["can_repair_whitespace"])
            self.assertNotIn(token, result.stdout)
            self.assertFalse(payload["token_printed"])

    def test_token_repair_whitespace_rewrites_only_repairable_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            token_file.write_text("123456789:\nabcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
            os.chmod(token_file, 0o600)
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "token-repair-whitespace", "--token-file", str(token_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["rewritten"])
            self.assertEqual(token_file.read_text(encoding="utf-8"), token + "\n")
            self.assertEqual(oct(token_file.stat().st_mode & 0o777), "0o600")
            self.assertNotIn(token, result.stdout)

    def test_token_set_from_stdin_writes_0600_without_printing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            token = "123456789:abcdefghijklmnopqrstuvwxyz"
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "token-set", "--token-file", str(token_file), "--stdin", "--json"],
                input=token + "\n",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(oct(token_file.stat().st_mode & 0o777), "0o600")
            self.assertEqual(token_file.read_text(encoding="utf-8"), token + "\n")
            self.assertNotIn(token, result.stdout)
            self.assertNotIn(token, result.stderr)

    def test_token_set_rejects_placeholder_or_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "telegram-token"
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "telegram", "token-set", "--token-file", str(token_file), "--stdin", "--json"],
                input="<bot-token>\n",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(token_file.exists())
            self.assertIn("digits:letters_digits", result.stderr)


if __name__ == "__main__":
    unittest.main()
