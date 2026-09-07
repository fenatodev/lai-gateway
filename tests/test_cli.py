from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway import __version__

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

    def test_cli_sessions_commands_proxy_without_printing_token(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            for args, expected_key in (
                (["sessions", "list", "--limit", "5"], "sessions"),
                (["sessions", "create"], "session"),
                (["sessions", "get", "s_test"], "session"),
                (["sessions", "delete", "s_test"], "deleted"),
            ):
                result = subprocess.run(
                    [sys.executable, "-m", "lai_gateway", *args],
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=10,
                    env=env,
                )
                payload = json.loads(result.stdout)
                self.assertIn(expected_key, payload)
                self.assertNotIn(TOKEN, result.stdout)
                self.assertEqual(result.stderr, "")


    def test_cli_runs_commands_proxy_read_only_without_printing_token(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            commands = (
                (["runs", "list", "--limit", "5"], "runs"),
                (["runs", "create", "--mode", "plan", "--task", "Summarize."], "run"),
                (["runs", "get", "cr_test"], "run"),
            )
            for args, expected_key in commands:
                result = subprocess.run(
                    [sys.executable, "-m", "lai_gateway", *args],
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=10,
                    env=env,
                )
                payload = json.loads(result.stdout)
                self.assertIn(expected_key, payload)
                self.assertNotIn(TOKEN, result.stdout)
                self.assertEqual(result.stderr, "")

    def test_cli_runs_create_rejects_write_mode(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "runs",
                "create",
                "--mode",
                "implement",
                "--task",
                "change files",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)


    def test_cli_doctor_json_and_open_ui_are_secret_free(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                "LAI_GATEWAY_PORT": "18787",
            }
            doctor = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "doctor", "--json"],
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
                env=env,
            )
            payload = json.loads(doctor.stdout)
            self.assertEqual(payload["overall"], "ready")
            self.assertNotIn(TOKEN, doctor.stdout)
            self.assertEqual(doctor.stderr, "")

            open_ui = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "open-ui", "--print-only"],
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
                env=env,
            )
            self.assertEqual(open_ui.stdout.strip(), "http://127.0.0.1:18787/")
            self.assertNotIn(TOKEN, open_ui.stdout)
            self.assertEqual(open_ui.stderr, "")


    def test_cli_dev_requires_ready_harness_before_serving(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:9",
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "dev", "--no-open"],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env=env,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("overall: blocked", result.stderr)
            self.assertIn("harness_status", result.stderr)
            self.assertNotIn(TOKEN, result.stderr)

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

    def test_cli_release_check_json_is_read_only_and_secret_free(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "release-check", "--target", __version__, "--json"],
            cwd=Path(__file__).parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertIn(proc.returncode, {0, 1})
        self.assertEqual(proc.stderr, "")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["product"], "lai-gateway")
        self.assertEqual(payload["target_version"], __version__)
        self.assertEqual(payload["expected_tag"], f"v{__version__}")
        self.assertIn(payload["overall"], {"ready", "blocked"})
        self.assertNotIn("test-token", proc.stdout)
        self.assertNotIn("Bearer ", proc.stdout)


if __name__ == "__main__":
    unittest.main()
