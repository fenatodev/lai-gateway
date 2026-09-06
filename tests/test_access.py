from __future__ import annotations

import json
import subprocess
import sys
import unittest

from lai_gateway.access import _windows_lan_hosts_from_rows, collect_mobile_access, render_mobile_access
from lai_gateway.qr import qr_svg


class MobileAccessTest(unittest.TestCase):
    def test_cli_mobile_access_json_is_secret_free(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "mobile-access", "--port", "18818", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "mobile-access")
        self.assertIn("qr_svg", payload)
        self.assertFalse(payload["security"]["qr_contains_token"])
        self.assertNotIn("Bearer", result.stdout)
        self.assertNotIn('"token":', result.stdout)

    def test_collect_mobile_access_prefers_tailscale_and_marks_portproxy_for_wsl(self) -> None:
        payload = collect_mobile_access(
            port=8787,
            bind="172.29.193.62",
            discovered_hosts=["172.29.193.62"],
            windows_hosts=["192.168.15.4"],
            tailscale_hosts=["100.107.179.6"],
            force_wsl=True,
        )
        self.assertEqual(payload["operation"], "mobile-access")
        self.assertEqual(payload["recommended_url"], "http://100.107.179.6:8787/")
        self.assertEqual(payload["recommended_kind"], "tailscale")
        self.assertIn("<svg", payload["qr_svg"])
        tailscale = payload["links"][0]
        self.assertTrue(tailscale["requires_portproxy"])
        self.assertIn("netsh interface portproxy add", tailscale["portproxy_command"])
        self.assertFalse(payload["security"]["qr_contains_token"])

    def test_render_mobile_access_is_actionable_and_secret_free(self) -> None:
        payload = collect_mobile_access(
            port=8787,
            bind="172.29.193.62",
            discovered_hosts=["172.29.193.62"],
            windows_hosts=["192.168.15.4"],
            tailscale_hosts=[],
            force_wsl=True,
        )
        rendered = render_mobile_access(payload)
        self.assertIn("recommended_url: http://192.168.15.4:8787/", rendered)
        self.assertIn("windows_portproxy", rendered)
        self.assertIn("QR is generated locally", rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertNotIn("token=", rendered)

    def test_wsl_loopback_uses_wsl_candidate_as_portproxy_target(self) -> None:
        payload = collect_mobile_access(
            port=8787,
            bind="127.0.0.1",
            discovered_hosts=["172.29.193.62"],
            windows_hosts=["192.168.15.4"],
            tailscale_hosts=["100.107.179.6"],
            force_wsl=True,
        )
        first = payload["links"][0]
        self.assertIn("connectaddress=172.29.193.62", first["portproxy_command"])
        self.assertTrue(any("Current gateway bind is loopback" in item for item in payload["warnings"]))

    def test_windows_lan_hosts_filter_virtual_wsl_and_tailscale_interfaces(self) -> None:
        rows = [
            {"IPAddress": "172.29.192.1", "InterfaceAlias": "vEthernet (WSL (Hyper-V firewall))"},
            {"IPAddress": "192.168.15.4", "InterfaceAlias": "Ethernet"},
            {"IPAddress": "100.107.179.6", "InterfaceAlias": "Tailscale"},
            {"IPAddress": "172.18.0.1", "InterfaceAlias": "DockerNAT"},
        ]
        self.assertEqual(_windows_lan_hosts_from_rows(rows), ["192.168.15.4"])

    def test_qr_svg_is_local_svg_and_rejects_long_payloads(self) -> None:
        svg = qr_svg("http://192.168.15.4:8787/")
        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)
        self.assertIn("QR code", svg)
        with self.assertRaises(Exception):
            qr_svg("x" * 200)


if __name__ == "__main__":
    unittest.main()
