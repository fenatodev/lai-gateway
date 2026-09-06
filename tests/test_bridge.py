from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from lai_gateway.bridge import collect_mobile_bridge, render_mobile_bridge
from lai_gateway.errors import ConfigError


class MobileBridgeTest(unittest.TestCase):
    def test_manual_bridge_plan_is_secret_free_and_actionable(self) -> None:
        payload = collect_mobile_bridge(
            port=8787,
            listen_ip="100.107.179.6",
            connect_ip="172.29.193.62",
        )
        rendered = render_mobile_bridge(payload)
        self.assertEqual(payload["url"], "http://100.107.179.6:8787/")
        self.assertFalse(payload["modifies_windows_network"])
        self.assertIn("netsh interface portproxy add", rendered)
        self.assertIn("connectaddress=172.29.193.62", rendered)
        self.assertNotIn("Current gateway bind is loopback", rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertNotIn("pair_token", rendered)
        self.assertFalse(payload["security"]["tokens_involved"])

    def test_rejects_unsafe_listen_and_connect_ips(self) -> None:
        with self.assertRaises(ConfigError):
            collect_mobile_bridge(port=8787, listen_ip="0.0.0.0", connect_ip="172.29.193.62")
        with self.assertRaises(ConfigError):
            collect_mobile_bridge(port=8787, listen_ip="8.8.8.8", connect_ip="172.29.193.62")
        with self.assertRaises(ConfigError):
            collect_mobile_bridge(port=8787, listen_ip="100.107.179.6", connect_ip="127.0.0.1")

    def test_apply_and_remove_use_injected_runner(self) -> None:
        calls: list[list[str]] = []

        def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

        applied = collect_mobile_bridge(
            port=8787,
            listen_ip="100.107.179.6",
            connect_ip="172.29.193.62",
            apply=True,
            runner=runner,
        )
        removed = collect_mobile_bridge(
            port=8787,
            listen_ip="100.107.179.6",
            connect_ip="172.29.193.62",
            remove=True,
            runner=runner,
        )
        self.assertTrue(applied["modifies_windows_network"])
        self.assertTrue(all(item["ok"] for item in applied["results"]))
        self.assertTrue(all(item["ok"] for item in removed["results"]))
        self.assertEqual(len(calls), 4)
        self.assertIn("portproxy add", calls[0][-1])
        self.assertIn("Remove-NetFirewallRule", calls[-1][-1])

    def test_target_resolution_uses_injected_mobile_access_payload(self) -> None:
        fake_access = {
            "environment": {"wsl": True},
            "warnings": [],
            "links": [
                {
                    "ip": "100.107.179.6",
                    "kind": "tailscale",
                    "url": "http://100.107.179.6:8787/",
                    "recommended": True,
                    "requires_portproxy": True,
                    "portproxy_command": "netsh interface portproxy add v4tov4 listenaddress=100.107.179.6 listenport=8787 connectaddress=172.29.193.62 connectport=8787",
                },
                {"ip": "172.29.193.62", "kind": "wsl-internal", "url": "http://172.29.193.62:8787/", "recommended": False},
            ],
        }
        with patch("lai_gateway.bridge.collect_mobile_access", return_value=fake_access):
            payload = collect_mobile_bridge(port=8787, target="recommended")
        self.assertEqual(payload["listen_ip"], "100.107.179.6")
        self.assertEqual(payload["connect_ip"], "172.29.193.62")


    def test_check_uses_injected_runner_without_mutation(self) -> None:
        calls: list[list[str]] = []

        def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            command = args[-1]
            if "portproxy show" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="100.107.179.6   8787   172.29.193.62   8787", stderr="")
            if "Get-NetFirewallRule" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"Enabled":"True","Action":"Allow","LocalPort":"8787","LocalAddress":"100.107.179.6"}', stderr="")
            if "172.29.193.62" in command or "100.107.179.6" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="True", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="unexpected")

        payload = collect_mobile_bridge(
            port=8787,
            listen_ip="100.107.179.6",
            connect_ip="172.29.193.62",
            check=True,
            runner=runner,
        )
        rendered = render_mobile_bridge(payload)
        self.assertFalse(payload["modifies_windows_network"])
        self.assertEqual(payload["check"]["overall"], "ready")
        self.assertEqual(len(calls), 4)
        self.assertIn("check: ready", rendered)
        self.assertNotIn("Bearer", json.dumps(payload) + rendered)

    def test_check_reports_warn_when_listen_target_fails(self) -> None:
        def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
            command = args[-1]
            if "portproxy show" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="100.107.179.6   8787   172.29.193.62   8787", stderr="")
            if "Get-NetFirewallRule" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"Enabled":"True","Action":"Allow","LocalPort":"8787","LocalAddress":"100.107.179.6"}', stderr="")
            if "172.29.193.62" in command:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="True", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="False", stderr="")

        payload = collect_mobile_bridge(
            port=8787,
            listen_ip="100.107.179.6",
            connect_ip="172.29.193.62",
            check=True,
            runner=runner,
        )
        self.assertEqual(payload["check"]["overall"], "warn")
        failures = [item["name"] for item in payload["check"]["results"] if not item["ok"]]
        self.assertEqual(failures, ["listen_target"])

    def test_cli_mobile_bridge_json_is_secret_free(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "mobile-bridge",
                "--listen-ip",
                "100.107.179.6",
                "--connect-ip",
                "172.29.193.62",
                "--port",
                "8787",
                "--json",
            ],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "mobile-bridge")
        self.assertEqual(payload["url"], "http://100.107.179.6:8787/")
        self.assertFalse(payload["modifies_windows_network"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)
        self.assertFalse(payload["security"]["pair_token_exposed"])
        self.assertFalse(payload["security"]["harness_token_exposed"])
