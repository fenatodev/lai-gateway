from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lai_gateway.errors import ConfigError
from lai_gateway.mobile import (
    collect_mobile_repair,
    collect_mobile_start,
    collect_mobile_status,
    prepare_mobile_serve_config,
    render_mobile_repair,
    render_mobile_start,
    render_mobile_status,
)


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

    def test_mobile_serve_blocks_existing_listener_before_mutating_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                with self.assertRaises(ConfigError) as ctx:
                    prepare_mobile_serve_config(
                        candidate_ip="192.168.7.52",
                        port=18806,
                        access_token_path=access,
                        pair_token_path=pair,
                    )
            self.assertIn("already has a listener", str(ctx.exception))
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

    def test_mobile_status_ready_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            collect_mobile_start(
                port=18807,
                prepare=True,
                show_pair=False,
                access_token_path=access,
                pair_token_path=pair,
                discovered_hosts=["192.168.7.53"],
            )
            access_secret = access.read_text(encoding="utf-8").strip()
            pair_secret = json.loads(pair.read_text(encoding="utf-8"))["token"]
            before = (access.read_text(encoding="utf-8"), pair.read_text(encoding="utf-8"))

            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_status(
                    candidate_ip="192.168.7.53",
                    port=18807,
                    access_token_path=access,
                    pair_token_path=pair,
                )
            rendered = render_mobile_status(payload)

            self.assertEqual(payload["overall"], "ready")
            self.assertTrue(payload["listener"]["active"])
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertEqual(before, (access.read_text(encoding="utf-8"), pair.read_text(encoding="utf-8")))
            self.assertNotIn(access_secret, rendered)
            self.assertNotIn(pair_secret, rendered)
            self.assertNotIn("Bearer", rendered)
            self.assertNotIn("qr_svg", payload["mobile_access"])
            self.assertFalse(payload["mobile_access"].get("qr_svg_included"))

    def test_mobile_status_reports_missing_pair_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            collect_mobile_start(
                port=18808,
                prepare=True,
                access_token_path=access,
                pair_token_path=pair,
                discovered_hosts=["192.168.7.54"],
            )
            pair.unlink()

            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_status(
                    candidate_ip="192.168.7.54",
                    port=18808,
                    access_token_path=access,
                    pair_token_path=pair,
                )

            self.assertEqual(payload["overall"], "needs_pair")
            self.assertFalse(pair.exists())
            self.assertIn("mobile-start --candidate-ip 192.168.7.54 --port 18808 --prepare --show-pair", "\n".join(payload["next_steps"]))

    def test_cli_mobile_status_json_uses_env_paths_without_creating_files(self) -> None:
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
                    "mobile-status",
                    "--candidate-ip",
                    "192.168.7.55",
                    "--port",
                    "18809",
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

            self.assertEqual(payload["operation"], "mobile-status")
            self.assertEqual(payload["overall"], "needs_prepare")
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertFalse(access.exists())
            self.assertFalse(pair.exists())
            self.assertNotIn("qr_svg", payload["mobile_access"])


    def test_mobile_repair_default_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_repair(
                    candidate_ip="192.168.7.56",
                    port=18810,
                    access_token_path=access,
                    pair_token_path=pair,
                )
            rendered = render_mobile_repair(payload)

            self.assertEqual(payload["operation"], "mobile-repair")
            self.assertEqual(payload["overall"], "needs_prepare")
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertFalse(payload["modifies_windows_network"])
            self.assertFalse(access.exists())
            self.assertFalse(pair.exists())
            self.assertNotIn("Bearer", rendered)
            self.assertFalse(payload["security"]["prints_tokens"])
            self.assertNotIn("qr_svg", payload["status_after"]["mobile_access"])

    def test_mobile_repair_prepare_refreshes_pair_without_printing_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp) / "access-token"
            pair = Path(tmp) / "pair-token.json"
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_repair(
                    candidate_ip="192.168.7.57",
                    port=18811,
                    prepare=True,
                    access_token_path=access,
                    pair_token_path=pair,
                )
            rendered = render_mobile_repair(payload)
            access_secret = access.read_text(encoding="utf-8").strip()
            pair_secret = json.loads(pair.read_text(encoding="utf-8"))["token"]

            self.assertEqual(payload["overall"], "ready")
            self.assertTrue(payload["modifies_files"])
            self.assertTrue(access.exists())
            self.assertTrue(pair.exists())
            self.assertNotIn(access_secret, rendered)
            self.assertNotIn(pair_secret, rendered)
            self.assertNotIn(pair_secret, json.dumps(payload, sort_keys=True))

    def test_mobile_repair_show_pair_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pair = Path(tmp) / "pair-token.json"
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_repair(
                    candidate_ip="192.168.7.58",
                    port=18812,
                    prepare=True,
                    show_pair=True,
                    access_token_path=Path(tmp) / "access-token",
                    pair_token_path=pair,
                )
            pair_secret = json.loads(pair.read_text(encoding="utf-8"))["token"]
            self.assertTrue(payload["security"]["prints_tokens"])
            self.assertIn(pair_secret, render_mobile_repair(payload))

    def test_mobile_repair_can_plan_bridge_without_applying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_repair(
                    candidate_ip="192.168.7.59",
                    port=18813,
                    bridge_listen_ip="100.107.179.6",
                    access_token_path=Path(tmp) / "access-token",
                    pair_token_path=Path(tmp) / "pair-token.json",
                )
            rendered = render_mobile_repair(payload)
            self.assertTrue(payload["bridge_needed"])
            self.assertFalse(payload["modifies_windows_network"])
            self.assertIn("netsh interface portproxy add", rendered)

    def test_mobile_repair_apply_bridge_uses_injected_runner(self) -> None:
        calls: list[list[str]] = []

        def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            with patch("lai_gateway.mobile._tcp_connects", return_value=True):
                payload = collect_mobile_repair(
                    candidate_ip="192.168.7.60",
                    port=18814,
                    bridge_listen_ip="100.107.179.6",
                    apply_bridge=True,
                    access_token_path=Path(tmp) / "access-token",
                    pair_token_path=Path(tmp) / "pair-token.json",
                    bridge_runner=runner,
                )

        self.assertEqual(payload["overall"], "needs_prepare")
        self.assertTrue(payload["modifies_windows_network"])
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(item["ok"] for item in payload["bridge"]["results"]))

    def test_cli_mobile_repair_prepare_uses_env_paths_and_is_secret_free(self) -> None:
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
                    "mobile-repair",
                    "--candidate-ip",
                    "192.168.7.61",
                    "--port",
                    "18815",
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
            pair_secret = json.loads(pair.read_text(encoding="utf-8"))["token"]

            self.assertEqual(payload["operation"], "mobile-repair")
            self.assertTrue(payload["modifies_files"])
            self.assertFalse(payload["modifies_windows_network"])
            self.assertNotIn(pair_secret, result.stdout)
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
