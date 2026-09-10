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
from lai_gateway.daily_config import validate_daily_config, write_daily_config
from lai_gateway.errors import GatewayError
from lai_gateway.ops import collect_ops_status, render_ops_status
from lai_gateway.telegram import write_telegram_chat_file
from lai_gateway.tokens import create_gateway_access_token, create_gateway_pairing_token

from .fake_harness import TOKEN, fake_harness


class OpsStatusTest(unittest.TestCase):
    def test_ops_status_ready_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            telegram_file = Path(tmp) / "telegram-token"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file)
            telegram_secret = "123456789:abcdefghijklmnopqrstuvwxyz"
            telegram_file.write_text(telegram_secret, encoding="utf-8")
            os.chmod(telegram_file, 0o600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                bind="192.168.7.62",
                port=18816,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            pair_secret = json.loads(pair_file.read_text(encoding="utf-8"))["token"]

            runs_file = Path(tmp) / "model-runs.jsonl"
            runs_file.write_text('{"operation":"model-eval","overall":"ready","elapsed_ms":42.0}\n', encoding="utf-8")
            with patch.dict(os.environ, {"LAI_GATEWAY_MODEL_RUNS_FILE": str(runs_file), "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json")}, clear=False), patch("lai_gateway.mobile._tcp_connects", return_value=True), patch("lai_gateway.ops.collect_model_status", return_value={"overall": "ready", "network_calls": {"local_openai_probe": True}}) as model_status:
                payload = collect_ops_status(
                    config=config,
                    mobile_candidate_ip="192.168.7.62",
                    telegram_token_file=telegram_file,
                    telegram_chat_id="123",
                    telegram_enable_send=True,
                )
            rendered = render_ops_status(payload)
            stdout = json.dumps(payload, sort_keys=True) + rendered

            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(payload["next_steps"], [])
            self.assertNotIn("next_steps:", rendered)
            model_status.assert_called_once_with(probe_openai=True)
            self.assertEqual(payload["model"]["overall"], "ready")
            self.assertTrue(payload["network_calls"]["model_local"])
            self.assertEqual(payload["model_runs"]["count"], 1)
            self.assertEqual(payload["mcp_broker"]["overall"], "ready")
            self.assertEqual(payload["mcp_broker"]["server_count"], 1)
            self.assertFalse(payload["mcp_broker"]["execution_enabled"])
            self.assertIn("harness_model: ready", rendered)
            self.assertIn("gateway_model_probe:", rendered)
            self.assertIn("mcp_broker: ready", rendered)
            self.assertIn("model_runs: 1", rendered)
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertNotIn(TOKEN, stdout)
            self.assertNotIn(pair_secret, stdout)
            self.assertNotIn(telegram_secret, stdout)
            self.assertNotIn("Bearer", stdout)

    def test_ops_status_uses_daily_config_mobile_defaults_when_candidate_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            root = Path(tmp)
            token_file = root / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config_path = root / "daily.json"
            daily = validate_daily_config(
                candidate_ip="192.168.7.66",
                port=18866,
                harness_repo=str(root / "harness"),
                path=config_path,
            )
            write_daily_config(daily, path=config_path)
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            mobile_payload = {
                "overall": "ready",
                "listener": {"active": True, "target": "192.168.7.66:18866"},
                "mobile_access": {"recommended_url": "http://192.168.7.66:18866/", "links": []},
                "next_steps": [],
            }
            with patch.dict(
                os.environ,
                {
                    "LAI_GATEWAY_DAILY_CONFIG": str(config_path),
                    "LAI_GATEWAY_MODEL_RUNS_FILE": str(root / "missing-model-runs.jsonl"),
                    "LAI_GATEWAY_MODEL_CONFIG_FILE": str(root / "missing-model.json"),
                },
                clear=False,
            ), patch("lai_gateway.ops.collect_mobile_status", return_value=mobile_payload) as mobile_status, patch(
                "lai_gateway.ops.collect_model_status",
                return_value={"overall": "ready", "network_calls": {"local_openai_probe": True}},
            ):
                payload = collect_ops_status(config=config)

        mobile_status.assert_called_once()
        self.assertEqual(mobile_status.call_args.kwargs["candidate_ip"], "192.168.7.66")
        self.assertEqual(mobile_status.call_args.kwargs["port"], 18866)
        self.assertEqual(payload["mobile"]["overall"], "ready")
        self.assertNotIn(TOKEN, json.dumps(payload, sort_keys=True))

    def test_ops_status_warns_for_optional_telegram_or_mobile_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)

            with patch.dict(os.environ, {"LAI_GATEWAY_MODEL_RUNS_FILE": str(Path(tmp) / "missing-model-runs.jsonl"), "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json")}):
                payload = collect_ops_status(
                    config=config,
                    mobile_candidate_ip="192.168.7.63",
                    mobile_port=18817,
                    telegram_token_file=Path(tmp) / "missing-telegram-token",
                )

            self.assertEqual(payload["overall"], "warn")
            self.assertEqual(payload["doctor"]["overall"], "ready")
            self.assertIn("Configure Telegram token", "\n".join(payload["next_steps"]))
            self.assertIn("Run local model evaluation metrics", "\n".join(payload["next_steps"]))


    def test_ops_status_warns_when_mcp_broker_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            telegram_file = Path(tmp) / "telegram-token"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file)
            telegram_file.write_text("123456789:abcdefghijklmnopqrstuvwxyz", encoding="utf-8")
            os.chmod(telegram_file, 0o600)
            runs_file = Path(tmp) / "model-runs.jsonl"
            runs_file.write_text('{"operation":"model-eval","overall":"ready","elapsed_ms":42.0}\n', encoding="utf-8")
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                bind="192.168.7.65",
                port=18819,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with patch.dict(os.environ, {"LAI_GATEWAY_MODEL_RUNS_FILE": str(runs_file), "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json")}, clear=False), \
                    patch("lai_gateway.mobile._tcp_connects", return_value=True), \
                    patch("lai_gateway.ops.HarnessClient.mcp_status", side_effect=GatewayError("mcp unavailable")):
                payload = collect_ops_status(
                    config=config,
                    mobile_candidate_ip="192.168.7.65",
                    telegram_token_file=telegram_file,
                    telegram_chat_id="123",
                    telegram_enable_send=True,
                )
        self.assertEqual(payload["overall"], "warn")
        self.assertEqual(payload["mcp_broker"]["overall"], "unknown")
        self.assertIn("Inspect MCP broker status", "\n".join(payload["next_steps"]))

    def test_cli_ops_status_json_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            telegram_file = Path(tmp) / "telegram-token"
            chat_file = Path(tmp) / "telegram-chat-id"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file)
            telegram_secret = "123456789:abcdefghijklmnopqrstuvwxyz"
            telegram_file.write_text(telegram_secret, encoding="utf-8")
            os.chmod(telegram_file, 0o600)
            write_telegram_chat_file(chat_id="123", chat_file=chat_file)
            pair_secret = json.loads(pair_file.read_text(encoding="utf-8"))["token"]
            env = dict(os.environ)
            env.update({
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                "LAI_GATEWAY_PRIVATE_BIND": "1",
                "LAI_GATEWAY_BIND": "192.168.7.64",
                "LAI_GATEWAY_PORT": "18818",
                "LAI_GATEWAY_ACCESS_TOKEN_FILE": str(access_file),
                "LAI_GATEWAY_PAIR_TOKEN_FILE": str(pair_file),
                "LAI_GATEWAY_TELEGRAM_ENABLE_SEND": "1",
                "LAI_GATEWAY_MODEL_RUNS_FILE": str(Path(tmp) / "missing-model-runs.jsonl"),
                "LAI_GATEWAY_MODEL_CONFIG_FILE": str(Path(tmp) / "missing-model.json"),
            })
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "ops-status",
                    "--candidate-ip",
                    "192.168.7.64",
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

            self.assertEqual(payload["operation"], "ops-status")
            self.assertEqual(payload["overall"], "warn")
            self.assertEqual(payload["mobile"]["overall"], "needs_server")
            self.assertIn("mcp_broker", payload)
            self.assertEqual(payload["mcp_broker"]["overall"], "ready")
            self.assertNotIn(TOKEN, result.stdout)
            self.assertNotIn(pair_secret, result.stdout)
            self.assertNotIn(telegram_secret, result.stdout)
            self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
