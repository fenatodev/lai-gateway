from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.errors import ConfigError
from lai_gateway.mobile import collect_mobile_start, prepare_mobile_serve_config, render_mobile_start


class MobileStartTest(unittest.TestCase):
    def test_mobile_start_default_is_read_only_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            payload = collect_mobile_start(
                port=18797,
                access_token_path=access,
                pair_token_path=pair,
                discovered_hosts=["127.0.0.1", "192.168.7.44"],
            )
            rendered = render_mobile_start(payload)

            self.assertEqual(payload["operation"], "mobile-start")
            self.assertEqual(payload["overall"], "needs_prepare")
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertFalse(access.exists())
            self.assertFalse(pair.exists())
            self.assertEqual(payload["preferred_url"], "http://192.168.7.44:18797/")
            self.assertIn("lai-gateway token create", rendered)
            self.assertIn("lai-gateway pair create --ttl-seconds 600 --show", rendered)
            self.assertNotIn("Bearer", rendered)
            self.assertNotIn('"token":', json.dumps(payload, sort_keys=True))

    def test_mobile_start_prepare_creates_tokens_without_printing_pair_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            payload = collect_mobile_start(
                port=18798,
                ttl_seconds=600,
                prepare=True,
                access_token_path=access,
                pair_token_path=pair,
                discovered_hosts=["192.168.7.45"],
            )
            stdout = json.dumps(payload, sort_keys=True)
            real_access = access.read_text(encoding="utf-8").strip()
            pair_doc = json.loads(pair.read_text(encoding="utf-8"))

            self.assertEqual(payload["overall"], "ready")
            self.assertTrue(payload["modifies_files"])
            self.assertTrue(access.exists())
            self.assertTrue(pair.exists())
            self.assertNotIn(real_access, stdout)
            self.assertNotIn(pair_doc["token"], stdout)
            self.assertFalse(any("pair_token" in action for action in payload["actions"]))

    def test_mobile_start_prepare_show_pair_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pair = Path(tmp) / "pair-token.json"
            payload = collect_mobile_start(
                port=18799,
                prepare=True,
                show_pair=True,
                access_token_path=Path(tmp) / "access-token",
                pair_token_path=pair,
                discovered_hosts=["192.168.7.46"],
            )
            pair_doc = json.loads(pair.read_text(encoding="utf-8"))
            self.assertTrue(any(action.get("pair_token") == pair_doc["token"] for action in payload["actions"]))

    def test_cli_mobile_start_prepare_uses_env_paths_and_is_secret_free_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            env = dict(os.environ)
            env["LAI_GATEWAY_ACCESS_TOKEN_FILE"] = str(access)
            env["LAI_GATEWAY_PAIR_TOKEN_FILE"] = str(pair)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "mobile-start",
                    "--candidate-ip",
                    "192.168.7.47",
                    "--port",
                    "18800",
                    "--prepare",
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
            real_access = access.read_text(encoding="utf-8").strip()
            pair_doc = json.loads(pair.read_text(encoding="utf-8"))

            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(payload["preferred_url"], "http://192.168.7.47:18800/")
            self.assertTrue(payload["modifies_files"])
            self.assertNotIn(real_access, result.stdout)
            self.assertNotIn(pair_doc["token"], result.stdout)
            self.assertNotIn("Bearer", result.stdout)


    def test_mobile_serve_prepares_private_config_after_candidate_is_unambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            payload, config = prepare_mobile_serve_config(
                candidate_ip="192.168.7.49",
                port=18803,
                access_token_path=access,
                pair_token_path=pair,
            )
            pair_doc = json.loads(pair.read_text(encoding="utf-8"))
            stdout = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["operation"], "mobile-serve")
            self.assertEqual(payload["overall"], "ready")
            self.assertTrue(payload["starts_server"])
            self.assertTrue(payload["modifies_files"])
            self.assertEqual(payload["serve"]["url"], "http://192.168.7.49:18803/")
            self.assertTrue(config.private_bind_enabled)
            self.assertEqual(config.bind, "192.168.7.49")
            self.assertEqual(oct(access.stat().st_mode & 0o777), "0o600")
            self.assertEqual(oct(pair.stat().st_mode & 0o777), "0o600")
            self.assertNotIn(access.read_text(encoding="utf-8").strip(), stdout)
            self.assertNotIn(pair_doc["token"], stdout)

    def test_mobile_serve_blocks_ambiguous_candidates_before_mutating_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            with self.assertRaises(ConfigError):
                prepare_mobile_serve_config(
                    port=18804,
                    access_token_path=access,
                    pair_token_path=pair,
                    discovered_hosts=["192.168.7.50", "10.7.0.50"],
                )
            self.assertFalse(access.exists())
            self.assertFalse(pair.exists())

    def test_cli_mobile_serve_prepares_then_fails_closed_when_harness_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            env = dict(os.environ)
            env["LAI_GATEWAY_ACCESS_TOKEN_FILE"] = str(access)
            env["LAI_GATEWAY_PAIR_TOKEN_FILE"] = str(pair)
            env["LAI_GATEWAY_HARNESS_URL"] = "http://127.0.0.1:9"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "mobile-serve",
                    "--candidate-ip",
                    "192.168.7.51",
                    "--port",
                    "18805",
                ],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            pair_doc = json.loads(pair.read_text(encoding="utf-8"))

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(access.exists())
            self.assertTrue(pair.exists())
            self.assertIn("lai-gateway mobile-serve: ready", result.stdout)
            self.assertIn("ui: http://192.168.7.51:18805/", result.stdout)
            self.assertIn("overall: blocked", result.stderr)
            self.assertNotIn(access.read_text(encoding="utf-8").strip(), result.stdout + result.stderr)
            self.assertNotIn(pair_doc["token"], result.stdout + result.stderr)
            self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_cli_mobile_start_show_pair_requires_prepare(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "mobile-start", "--show-pair", "--candidate-ip", "192.168.7.48"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--show-pair requires --prepare", result.stderr)


if __name__ == "__main__":
    unittest.main()
