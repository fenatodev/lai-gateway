from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lai_gateway.config import GatewayConfig
from lai_gateway.health import collect_health_report, render_health_report
from lai_gateway.telegram import write_telegram_chat_file
from lai_gateway.tokens import create_gateway_access_token, create_gateway_pairing_token

from .fake_harness import TOKEN, fake_harness


class HealthReportTest(unittest.TestCase):
    def test_health_report_is_compact_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            telegram_file = Path(tmp) / "telegram-token"
            runs_file = Path(tmp) / "model-runs.jsonl"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file)
            telegram_secret = "123456789:abcdefghijklmnopqrstuvwxyz"
            telegram_file.write_text(telegram_secret, encoding="utf-8")
            os.chmod(telegram_file, 0o600)
            runs_file.write_text(
                '{"operation":"model-eval","overall":"ready","elapsed_ms":42.0}\n',
                encoding="utf-8",
            )
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                bind="192.168.7.80",
                port=18830,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            pair_secret = json.loads(pair_file.read_text(encoding="utf-8"))["token"]

            with patch.dict(
                os.environ,
                {
                    "LAI_GATEWAY_MODEL_RUNS_FILE": str(runs_file),
                    "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json"),
                },
                clear=False,
            ), patch("lai_gateway.mobile._tcp_connects", return_value=True), patch(
                "lai_gateway.ops.collect_model_status",
                return_value={"overall": "ready", "network_calls": {"local_openai_probe": True}},
            ):
                payload = collect_health_report(
                    config=config,
                    mobile_candidate_ip="192.168.7.80",
                    telegram_token_file=telegram_file,
                    telegram_chat_id="123",
                    telegram_enable_send=True,
                )

            rendered = render_health_report(payload)
            combined = json.dumps(payload, sort_keys=True) + rendered
            self.assertEqual(payload["operation"], "health-report")
            self.assertEqual(payload["overall"], "ready")
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertEqual(payload["checks"]["doctor"], "ready")
            self.assertEqual(payload["checks"]["mobile"], "ready")
            self.assertEqual(payload["checks"]["mcp_broker"], "ready")
            self.assertEqual(payload["checks"]["model_runs"], 1)
            self.assertFalse(payload["mcp"]["execution_enabled"])
            self.assertTrue(payload["mobile"]["listener_active"])
            self.assertEqual(payload["next_steps"], [])
            self.assertIn("lai-gateway health-report: ready", rendered)
            self.assertIn("mcp_broker: ready", rendered)
            self.assertIn("security: tokens=false", rendered)
            self.assertNotIn(TOKEN, combined)
            self.assertNotIn(pair_secret, combined)
            self.assertNotIn(telegram_secret, combined)
            self.assertNotIn("Bearer", combined)

    def test_cli_health_report_json_and_telegram_notify_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            telegram_file = Path(tmp) / "telegram-token"
            chat_file = Path(tmp) / "telegram-chat-id"
            runs_file = Path(tmp) / "model-runs.jsonl"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file)
            telegram_secret = "123456789:abcdefghijklmnopqrstuvwxyz"
            telegram_file.write_text(telegram_secret, encoding="utf-8")
            os.chmod(telegram_file, 0o600)
            write_telegram_chat_file(chat_id="123", chat_file=chat_file)
            pair_secret = json.loads(pair_file.read_text(encoding="utf-8"))["token"]
            runs_file.write_text(
                '{"operation":"model-eval","overall":"ready","elapsed_ms":42.0}\n',
                encoding="utf-8",
            )
            env = dict(os.environ)
            env.update(
                {
                    "LAI_GATEWAY_HARNESS_URL": harness.url,
                    "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                    "LAI_GATEWAY_PRIVATE_BIND": "1",
                    "LAI_GATEWAY_BIND": "192.168.7.81",
                    "LAI_GATEWAY_PORT": "18831",
                    "LAI_GATEWAY_ACCESS_TOKEN_FILE": str(access_file),
                    "LAI_GATEWAY_PAIR_TOKEN_FILE": str(pair_file),
                    "LAI_GATEWAY_TELEGRAM_ENABLE_SEND": "1",
                    "LAI_GATEWAY_TELEGRAM_CHAT_FILE": str(chat_file),
                    "LAI_GATEWAY_MODEL_RUNS_FILE": str(runs_file),
                    "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json"),
                }
            )

            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "lai_gateway",
                        "health-report",
                        "--candidate-ip",
                        "192.168.7.81",
                        "--telegram-token-file",
                        str(telegram_file),
                        "--telegram-chat-id",
                        "123",
                        "--json",
                    ],
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=10,
                )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "health-report")
            self.assertIn(payload["overall"], {"ready", "warn"})
            self.assertFalse(payload["security"]["prints_tokens"])
            self.assertNotIn(TOKEN, result.stdout + result.stderr)
            self.assertNotIn(pair_secret, result.stdout + result.stderr)
            self.assertNotIn(telegram_secret, result.stdout + result.stderr)
            self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_cli_health_report_telegram_notify_uses_report_text_without_secrets(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        from lai_gateway.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:8765",
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                "LAI_GATEWAY_TELEGRAM_ENABLE_SEND": "1",
            }
            report = {
                "operation": "health-report",
                "overall": "ready",
                "version": "0.1.34",
                "starts_server": False,
                "modifies_files": False,
                "network_calls": {"harness_local": True, "model_local": True},
                "checks": {
                    "doctor": "ready",
                    "harness_model": "ready",
                    "mobile": "ready",
                    "telegram": "ready",
                    "gateway_model_probe": "ready",
                    "model_runs": 1,
                    "mcp_broker": "ready",
                },
                "mcp": {"server_count": 1, "execution_enabled": False},
                "mobile": {"listener_active": True},
                "telegram": {"send_enabled": True},
                "security": {
                    "prints_tokens": False,
                    "prints_pairing_secret": False,
                    "prints_chat_reference": False,
                    "prints_harness_token": False,
                    "starts_server": False,
                    "modifies_files": False,
                },
                "next_steps": [],
            }
            with patch.dict(os.environ, env, clear=False), patch(
                "lai_gateway.__main__.collect_health_report", return_value=report
            ) as collect, patch(
                "lai_gateway.__main__.send_telegram_message",
                return_value={"ok": True, "message_id": 77},
            ) as send:
                out = StringIO()
                with redirect_stdout(out):
                    code = main(["health-report", "--telegram-notify", "--json"])

        self.assertEqual(code, 0)
        collect.assert_called_once()
        send.assert_called_once()
        sent_text = send.call_args.kwargs["text"]
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["telegram_notify"]["message_id"], 77)
        self.assertIn("lai-gateway health-report: ready", sent_text)
        combined = out.getvalue() + sent_text
        self.assertNotIn(TOKEN, combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("chat_id", combined)


if __name__ == "__main__":
    unittest.main()
