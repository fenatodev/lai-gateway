from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.config import GatewayConfig
from lai_gateway.service import (
    collect_service_plan,
    install_service_unit,
    remove_service_unit,
    render_service_install,
    render_service_plan,
)

from .fake_harness import TOKEN


class ServiceTest(unittest.TestCase):
    def _config(self, tmp: str) -> GatewayConfig:
        token_file = Path(tmp) / "control-token"
        access_file = Path(tmp) / "access-token"
        pair_file = Path(tmp) / "pair-token.json"
        token_file.write_text(TOKEN, encoding="utf-8")
        access_file.write_text("a" * 40 + "\n", encoding="utf-8")
        pair_file.write_text("{}\n", encoding="utf-8")
        return GatewayConfig(
            harness_url="http://127.0.0.1:8765",
            token_file=token_file,
            bind="127.0.0.1",
            port=8787,
            private_bind_enabled=False,
            access_token_file=access_file,
            pair_token_file=pair_file,
        )

    def test_service_plan_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp)
            payload = collect_service_plan(
                config=config,
                candidate_ip="192.168.7.70",
                port=18830,
                unit_path=Path(tmp) / "lai-gateway-mobile.service",
                python_bin=sys.executable,
                repo_dir=Path(tmp),
                telegram_notify=True,
            )
            rendered = render_service_plan(payload)
            combined = json.dumps(payload, sort_keys=True) + rendered

            self.assertEqual(payload["operation"], "service-plan")
            self.assertFalse(payload["starts_server"])
            self.assertFalse(payload["modifies_files"])
            self.assertIn("mobile-serve", payload["unit_text"])
            self.assertIn("--telegram-notify", payload["unit_text"])
            self.assertIn("LAI_GATEWAY_PRIVATE_BIND=1", payload["unit_text"])
            self.assertNotIn(TOKEN, combined)
            self.assertNotIn("Bearer", combined)
            self.assertFalse(payload["security"]["stores_token_values"])

    def test_service_install_writes_unit_but_does_not_start_systemd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp)
            unit_path = Path(tmp) / "unit.service"
            payload = install_service_unit(
                config=config,
                candidate_ip="192.168.7.71",
                port=18831,
                unit_path=unit_path,
                python_bin=sys.executable,
                repo_dir=Path(tmp),
            )
            rendered = render_service_install(payload)

            self.assertTrue(unit_path.exists())
            self.assertEqual(oct(unit_path.stat().st_mode & 0o777), "0o644")
            self.assertTrue(payload["modifies_files"])
            self.assertFalse(payload["modifies_systemd"])
            self.assertIn("systemctl --user enable --now", rendered)
            self.assertIn("ExecStart", unit_path.read_text(encoding="utf-8"))
            with self.assertRaises(Exception):
                install_service_unit(
                    config=config,
                    candidate_ip="192.168.7.71",
                    port=18831,
                    unit_path=unit_path,
                    python_bin=sys.executable,
                    repo_dir=Path(tmp),
                )

    def test_service_remove_deletes_unit_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_path = Path(tmp) / "unit.service"
            unit_path.write_text("[Unit]\nDescription=x\n", encoding="utf-8")
            payload = remove_service_unit(unit_path=unit_path)
            again = remove_service_unit(unit_path=unit_path)

            self.assertTrue(payload["removed"])
            self.assertFalse(unit_path.exists())
            self.assertFalse(again["removed"])

    def test_cli_service_plan_json_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "control-token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file.write_text("a" * 40 + "\n", encoding="utf-8")
            pair_file.write_text("{}\n", encoding="utf-8")
            env = dict(os.environ)
            env.update({
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                "LAI_GATEWAY_ACCESS_TOKEN_FILE": str(access_file),
                "LAI_GATEWAY_PAIR_TOKEN_FILE": str(pair_file),
            })
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "service-plan",
                    "--candidate-ip",
                    "192.168.7.72",
                    "--port",
                    "18832",
                    "--unit-path",
                    str(Path(tmp) / "unit.service"),
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

            self.assertEqual(payload["operation"], "service-plan")
            self.assertEqual(payload["url"], "http://192.168.7.72:18832/")
            self.assertNotIn(TOKEN, result.stdout)
            self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
