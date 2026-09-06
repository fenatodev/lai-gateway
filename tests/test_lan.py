from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.lan import _safe_lan_ip, collect_lan_info, render_lan_info


class LanInfoTest(unittest.TestCase):
    def test_collect_lan_info_filters_to_private_non_loopback_candidates(self) -> None:
        payload = collect_lan_info(
            port=18787,
            discovered_hosts=[
                "127.0.0.1",
                "::1",
                "0.0.0.0",
                "8.8.8.8",
                "169.254.1.1",
                "192.168.1.20",
                "192.168.1.20",
                "10.0.0.8",
                "172.16.4.5",
                "fc00::1",
                "not-an-ip",
            ],
        )

        self.assertEqual([item["ip"] for item in payload["candidates"]], ["192.168.1.20", "10.0.0.8", "172.16.4.5", "fc00::1"])
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertTrue(payload["security"]["private_bind_is_opt_in"])
        self.assertFalse(payload["security"]["wildcard_bind_allowed"])
        self.assertFalse(payload["security"]["public_bind_allowed"])
        first_command = payload["candidates"][0]["dev_command"]
        self.assertIn("LAI_GATEWAY_PRIVATE_BIND=1", first_command)
        self.assertIn("LAI_GATEWAY_BIND=192.168.1.20", first_command)
        self.assertIn("${HOME}/.config/lai-gateway/access-token", first_command)
        self.assertIn("lai-gateway dev --no-open", first_command)

    def test_safe_lan_ip_rejects_unsafe_addresses(self) -> None:
        for raw in ["127.0.0.1", "::1", "0.0.0.0", "8.8.8.8", "169.254.1.1", "224.0.0.1"]:
            self.assertIsNone(_safe_lan_ip(raw))
        self.assertEqual(str(_safe_lan_ip("192.168.1.10")), "192.168.1.10")
        self.assertEqual(str(_safe_lan_ip("10.10.0.2")), "10.10.0.2")

    def test_render_lan_info_is_secret_free_and_actionable(self) -> None:
        payload = collect_lan_info(port=8787, discovered_hosts=["192.168.1.20"])
        rendered = render_lan_info(payload)
        self.assertIn("lai-gateway lan-info", rendered)
        self.assertIn("starts_server: false", rendered)
        self.assertIn("modifies_files: false", rendered)
        self.assertIn("http://192.168.1.20:8787/", rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertNotIn("token=", rendered)

    def test_cli_lan_info_json_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            marker.write_text("unchanged", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "lan-info", "--port", "18787", "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertEqual(marker.read_text(encoding="utf-8"), "unchanged")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "lan-info")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertNotIn("Bearer", result.stdout)
        self.assertNotIn('"token":', result.stdout)


if __name__ == "__main__":
    unittest.main()
