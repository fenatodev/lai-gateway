from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway import __version__

from .fake_harness import TOKEN, fake_harness
from .fixtures import CONTRACT


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ScriptTest(unittest.TestCase):

    def test_makefile_exposes_check_and_milestone_stack_gate(self) -> None:
        makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")
        self.assertIn("node --check lai_gateway/static/app.js", makefile)
        self.assertIn("bash scripts/publication-scan.sh", makefile)
        self.assertIn("node not found; skipping JS syntax check", makefile)
        self.assertIn("milestone-gate: check", makefile)
        self.assertIn("scripts/stack-check.sh", makefile)
        self.assertIn("--json | $(PYTHON) -c", makefile)
        self.assertIn("ready_for_local_commit", makefile)

    def test_install_local_writes_secret_free_wrappers_to_requested_bin_dir(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            env = {**os.environ, "LAI_GATEWAY_INSTALL_BIN": str(bin_dir), "PYTHON": sys.executable}
            result = subprocess.run(
                ["bash", "scripts/install-local.sh"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            gateway = bin_dir / "lai-gateway"
            ui = bin_dir / "lai-gateway-ui"
            mobile = bin_dir / "lai-gateway-mobile"
            model = bin_dir / "lai-gateway-model"
            mobile_proxy = bin_dir / "lai-gateway-mobile-proxy"
            daily = bin_dir / "lai-gateway-daily"
            stack_check = bin_dir / "lai-gateway-stack-check"
            self.assertTrue(gateway.exists())
            self.assertTrue(ui.exists())
            self.assertTrue(mobile.exists())
            self.assertTrue(model.exists())
            self.assertTrue(mobile_proxy.exists())
            self.assertTrue(daily.exists())
            self.assertTrue(stack_check.exists())
            self.assertIn(f"lai-gateway {__version__}", result.stdout)
            self.assertNotIn("TOKEN", gateway.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", ui.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", mobile.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", model.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", mobile_proxy.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", daily.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", stack_check.read_text(encoding="utf-8").upper())
            self.assertIn("repo_dir=", ui.read_text(encoding="utf-8"))
            self.assertIn("repo_dir=", mobile.read_text(encoding="utf-8"))
            self.assertIn("repo_dir=", model.read_text(encoding="utf-8"))
            self.assertIn("mobile-proxy", mobile_proxy.read_text(encoding="utf-8"))
            self.assertIn("launch-daily.sh", daily.read_text(encoding="utf-8"))
            self.assertIn("stack-check.sh", stack_check.read_text(encoding="utf-8"))
            mobile_help = subprocess.run(
                [str(mobile), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("lai-gateway-mobile", mobile_help.stdout)
            model_help = subprocess.run(
                [str(model), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("lai-gateway-model", model_help.stdout)
            proxy_help = subprocess.run(
                [str(mobile_proxy), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("mobile-proxy", proxy_help.stdout)
            daily_help = subprocess.run(
                [str(daily), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("lai-gateway-daily", daily_help.stdout)
            stack_help = subprocess.run(
                [str(stack_check), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("stack-check", stack_help.stdout)
            version = subprocess.run(
                [str(gateway), "--version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertEqual(version.stdout.strip(), f"lai-gateway {__version__}")


    def test_publication_scan_blocks_private_local_paths_known_ips_and_blocked_prose(self) -> None:
        repo = Path(__file__).parents[1]
        good = subprocess.run(
            ["bash", "scripts/publication-scan.sh"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        self.assertIn("Publication scan passed", good.stdout)
        leak_cases = (
            "bad /home/fenato/dev/projects path\n",
            "bad /mnt/c/Users/someone/project path\n",
            "bad C:\\Users\\someone\\project path\n",
            "bad 172.29.193.62 local WSL IP\n",
            "bad 100.107.179.6 local tailnet IP\n",
            "bad 192.168.15.4 local LAN IP\n",
            "Humanity has made many mistakes in release docs\n",
            "Tiny mercy in a world full of tracking pixels\n",
        )
        for idx, content in enumerate(leak_cases):
            with tempfile.TemporaryDirectory() as tmp:
                leak = Path(tmp) / f"leak-{idx}.md"
                leak.write_text(content, encoding="utf-8")
                bad = subprocess.run(
                    ["bash", "scripts/publication-scan.sh", str(leak)],
                    cwd=repo,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=10,
                )
            self.assertEqual(bad.returncode, 1)
            self.assertIn("publication scan failed", bad.stderr)

    def test_pyproject_declares_build_system_console_script_and_package_data(self) -> None:
        repo = Path(__file__).parents[1]
        import tomllib

        with (repo / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)

        self.assertEqual(
            pyproject["build-system"]["build-backend"],
            "setuptools.build_meta",
        )
        self.assertIn("setuptools>=69", pyproject["build-system"]["requires"])
        self.assertEqual(
            pyproject["project"]["scripts"]["lai-gateway"],
            "lai_gateway.__main__:main",
        )
        package_find = pyproject["tool"]["setuptools"]["packages"]["find"]
        self.assertEqual(package_find["where"], ["."])
        self.assertEqual(package_find["include"], ["lai_gateway*"])
        self.assertIn("tests*", package_find["exclude"])
        self.assertIn("docs*", package_find["exclude"])
        self.assertIn("scripts*", package_find["exclude"])
        self.assertIn(
            "static/*",
            pyproject["tool"]["setuptools"]["package-data"]["lai_gateway"],
        )


    def test_gitignore_excludes_private_runtime_and_build_artifacts(self) -> None:
        repo = Path(__file__).parents[1]
        ignored_paths = (
            ".pytest_cache/cache",
            ".mypy_cache/cache",
            ".ruff_cache/cache",
            ".venv/pyvenv.cfg",
            ".env",
            ".env.local",
            ".secrets/model-api-key",
            "dist/lai_gateway-0.1.31-py3-none-any.whl",
            "build/temp",
            "lai_gateway.egg-info/PKG-INFO",
            "release.vsix",
            "debug.log",
            "private.key",
            "api-key",
            "events.jsonl",
            "current-context.json",
            "models/example.gguf",
            "runtime.sqlite",
            "runtime.sqlite3",
            "htmlcov/index.html",
        )
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=repo,
            input="\n".join(ignored_paths) + "\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.splitlines()), set(ignored_paths))

        env_example = subprocess.run(
            ["git", "check-ignore", ".env.example"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(env_example.returncode, 0)



    def test_mobile_readonly_dogfood_script_uses_sanitized_read_only_loop(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "PYTHON": sys.executable,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
                "LAI_GATEWAY_DOGFOOD_POLL_LIMIT": "2",
                "LAI_GATEWAY_DOGFOOD_POLL_SECONDS": "0",
            }
            result = subprocess.run(
                ["bash", "scripts/mobile-readonly-dogfood.sh"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=20,
            )

        self.assertIn("write-mode rejection: ok", result.stdout)
        self.assertIn("session-create: sanitized", result.stdout)
        self.assertIn("run-create: sanitized", result.stdout)
        self.assertIn("run-get: sanitized", result.stdout)
        self.assertIn("run-events: sanitized", result.stdout)
        self.assertIn("session-delete: sanitized", result.stdout)
        self.assertIn("mobile-readonly-dogfood: ready", result.stdout)
        self.assertNotIn(TOKEN, result.stdout)
        self.assertNotIn("/home/", result.stdout)
        self.assertNotIn("chat_id", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_stack_check_validates_fake_harness_without_printing_secrets(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            harness_repo = Path(tmp) / "lai-local-agent"
            src = harness_repo / "src"
            src.mkdir(parents=True)
            fake_agent = src / "local-agent"
            fake_agent.write_text(
                "from __future__ import annotations\n"
                "import json, sys\n"
                f"CONTRACT = {CONTRACT!r}\n"
                "args = sys.argv[1:]\n"
                "if args == ['--version']:\n"
                "    print('lai harness 0.4.7')\n"
                "elif args == ['--gateway-contract', '--json']:\n"
                "    print(json.dumps(CONTRACT, sort_keys=True))\n"
                "elif args[:2] == ['--mcp', 'status'] and args[2:] == ['--help']:\n"
                "    print('Usage: lai mcp status [--json]')\n"
                "elif args[:2] == ['--mcp', 'tools'] and args[2:] == ['--help']:\n"
                "    print('Usage: lai mcp tools [--json]')\n"
                "elif args[:2] == ['--mcp', 'policy-check'] and args[2:] == ['--help']:\n"
                "    print('Usage: lai mcp policy-check --operation status|list-tools|call-tool [--server NAME] [--tool NAME] [--json]')\n"
                "elif args[:2] == ['--mcp', 'status'] and '--json' in args:\n"
                "    print(json.dumps({'product': 'lai harness', 'version': '0.4.7', 'overall': 'no_config', 'server_count': 0, 'config_files': [], 'servers': [], 'issues': [], 'security': {'executes_tools': False, 'prints_credentials': False, 'reads_env_values': False}}, sort_keys=True))\n"
                "elif args[:2] == ['--mcp', 'policy-check'] and '--json' in args:\n"
                "    print(json.dumps({'product': 'lai harness', 'version': '0.4.7', 'decision': 'DENY', 'reason': 'MCP tool execution is not enabled in this foundation milestone', 'executed': False}, sort_keys=True))\n"
                "else:\n"
                "    raise SystemExit(2)\n",
                encoding="utf-8",
            )
            env = {**os.environ, "PYTHON": sys.executable}
            result = subprocess.run(
                [
                    "bash",
                    "scripts/stack-check.sh",
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--min-harness",
                    "0.4.6",
                ],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=20,
            )
            combined = result.stdout + result.stderr
            self.assertIn("overall: ready_for_local_commit", result.stdout)
            self.assertIn("gateway_contract_compatible", result.stdout)
            self.assertIn("harness_mcp_call_tool_denied", result.stdout)
            self.assertIn("gateway_release_check_version_and_safety", result.stdout)
            self.assertNotIn("Bearer", combined)
            self.assertNotIn(TOKEN, combined)
            self.assertNotIn("API_KEY", combined)

            json_result = subprocess.run(
                [
                    "bash",
                    "scripts/stack-check.sh",
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--min-harness",
                    "0.4.6",
                    "--json",
                ],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=20,
            )
            json_payload = json.loads(json_result.stdout)
            json_combined = json_result.stdout + json_result.stderr
            self.assertEqual(json_payload["overall"], "ready_for_local_commit")
            self.assertEqual(json_payload["gateway_version"], __version__)
            self.assertEqual(json_payload["harness_version"], "0.4.7")
            self.assertEqual(json_payload["minimum_harness"], "0.4.6")
            self.assertIsNone(json_payload["target_harness"])
            self.assertEqual(json_payload["harness_compatibility"], "minimum")
            self.assertIn(
                "gateway_release_check_version_and_safety",
                {check["name"] for check in json_payload["checks"]},
            )
            self.assertIn(
                "harness_mcp_call_tool_denied",
                {check["name"] for check in json_payload["checks"]},
            )
            self.assertNotIn("Bearer", json_combined)
            self.assertNotIn(TOKEN, json_combined)
            self.assertNotIn("API_KEY", json_combined)

            non_repo_json_result = subprocess.run(
                [
                    "bash",
                    str(repo / "scripts" / "stack-check.sh"),
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--min-harness",
                    "0.4.6",
                    "--json",
                ],
                cwd=tmp,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=20,
            )
            non_repo_payload = json.loads(non_repo_json_result.stdout)
            non_repo_combined = non_repo_json_result.stdout + non_repo_json_result.stderr
            self.assertEqual(non_repo_payload["overall"], "ready_for_local_commit")
            self.assertEqual(non_repo_payload["gateway_version"], __version__)
            self.assertNotIn("Bearer", non_repo_combined)
            self.assertNotIn(TOKEN, non_repo_combined)
            self.assertNotIn("API_KEY", non_repo_combined)

            too_new_minimum = subprocess.run(
                [
                    "bash",
                    "scripts/stack-check.sh",
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--min-harness",
                    "0.4.8",
                ],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            too_new_combined = too_new_minimum.stdout + too_new_minimum.stderr
            self.assertNotEqual(too_new_minimum.returncode, 0)
            self.assertIn("is below minimum", too_new_minimum.stderr)
            self.assertNotIn("Bearer", too_new_combined)
            self.assertNotIn(TOKEN, too_new_combined)

            exact_target = subprocess.run(
                [
                    "bash",
                    "scripts/stack-check.sh",
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--target-harness",
                    "0.4.7",
                    "--json",
                ],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=20,
            )
            exact_payload = json.loads(exact_target.stdout)
            self.assertEqual(exact_payload["harness_compatibility"], "exact")
            self.assertEqual(exact_payload["target_harness"], "0.4.7")
            self.assertEqual(exact_payload["minimum_harness"], "0.4.6")

            wrong_target = subprocess.run(
                [
                    "bash",
                    "scripts/stack-check.sh",
                    "--harness-repo",
                    str(harness_repo),
                    "--target-gateway",
                    __version__,
                    "--target-harness",
                    "0.4.4",
                ],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            wrong_combined = wrong_target.stdout + wrong_target.stderr
            self.assertNotEqual(wrong_target.returncode, 0)
            self.assertIn("does not match target", wrong_target.stderr)
            self.assertNotIn("Bearer", wrong_combined)
            self.assertNotIn(TOKEN, wrong_combined)

    def test_launch_daily_help_check_only_and_missing_candidate_are_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        help_result = subprocess.run(
            ["bash", "scripts/launch-daily.sh", "--help"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        missing = subprocess.run(
            ["bash", "scripts/launch-daily.sh"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            env={**os.environ, "LAI_GATEWAY_DAILY_CONFIG": str(repo / ".missing-daily-config"), "PYTHON": sys.executable},
        )
        env = {**os.environ, "LAI_GATEWAY_PHONE_URL": "http://example.tailnet.ts.net:8787/", "PYTHON": sys.executable}
        check_only = subprocess.run(
            [
                "bash",
                "scripts/launch-daily.sh",
                "--candidate-ip",
                "172.29.193.62",
                "--check-only",
                "--skip-model",
                "--skip-harness",
                "--skip-mobile",
                "--skip-proxy",
            ],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        combined = help_result.stdout + help_result.stderr + missing.stdout + missing.stderr + check_only.stdout + check_only.stderr
        self.assertIn("lai-gateway-daily", help_result.stdout)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("daily-config set", missing.stderr)
        self.assertIn("check_only: true", check_only.stdout)
        self.assertIn("phone_url: http://example.tailnet.ts.net:8787/", check_only.stdout)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn(TOKEN, combined)
    def test_launchers_refuse_noninteractive_show_pair(self) -> None:
        repo = Path(__file__).parents[1]
        env = {**os.environ, "LAI_GATEWAY_DAILY_CONFIG": str(repo / ".missing-daily-config"), "PYTHON": sys.executable}
        cases = (
            ["bash", "scripts/launch-daily.sh", "--candidate-ip", "172.29.193.62", "--show-pair", "--check-only", "--skip-model", "--skip-harness", "--skip-mobile", "--skip-proxy"],
            ["bash", "scripts/launch-mobile.sh", "--candidate-ip", "172.29.193.62", "--show-pair"],
        )
        for command in cases:
            with self.subTest(command=command[1]):
                result = subprocess.run(
                    command,
                    cwd=repo,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=10,
                )
                combined = result.stdout + result.stderr
                self.assertEqual(result.returncode, 2)
                self.assertIn("interactive terminal", result.stderr)
                self.assertNotIn("pair_token", combined)
                self.assertNotIn(TOKEN, combined)
                self.assertNotIn("Bearer", combined)


    def test_launch_daily_uses_daily_config_defaults(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "daily.json"
            set_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "daily-config",
                    "set",
                    "--candidate-ip",
                    "172.29.193.62",
                    "--phone-url",
                    "http://example.tailnet.ts.net:8787/",
                    "--harness-repo",
                    str(repo),
                    "--path",
                    str(config_path),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            payload = json.loads(set_result.stdout)
            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
            env_result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "daily-config", "env", "--path", str(config_path)],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("LAI_GATEWAY_MOBILE_IP=172.29.193.62", env_result.stdout)
            self.assertIn("LAI_GATEWAY_PHONE_URL=http://example.tailnet.ts.net:8787/", env_result.stdout)
            env = {**os.environ, "LAI_GATEWAY_DAILY_CONFIG": str(config_path), "PYTHON": sys.executable}
            env.pop("LAI_GATEWAY_MOBILE_IP", None)
            check_only = subprocess.run(
                ["bash", "scripts/launch-daily.sh", "--check-only"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("daily_config: loaded", check_only.stdout)
            self.assertIn("mobile_target: 172.29.193.62:8787", check_only.stdout)
            self.assertIn("phone_url: http://example.tailnet.ts.net:8787/", check_only.stdout)
            combined = set_result.stdout + set_result.stderr + env_result.stdout + env_result.stderr + check_only.stdout + check_only.stderr
            self.assertNotIn("Bearer", combined)
            self.assertNotIn(TOKEN, combined)

    def test_daily_config_rejects_unsafe_values(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            bad_public_ip = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "daily-config", "set", "--candidate-ip", "8.8.8.8", "--path", str(Path(tmp) / "daily.json")],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            bad_url = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "daily-config",
                    "set",
                    "--candidate-ip",
                    "172.29.193.62",
                    "--phone-url",
                    "https://example.tailnet.ts.net:8787/",
                    "--path",
                    str(Path(tmp) / "daily.json"),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        self.assertNotEqual(bad_public_ip.returncode, 0)
        self.assertIn("private non-loopback", bad_public_ip.stderr)
        self.assertNotEqual(bad_url.returncode, 0)
        self.assertIn("http://", bad_url.stderr)

    def test_launch_mobile_help_and_missing_candidate_are_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        help_result = subprocess.run(
            ["bash", "scripts/launch-mobile.sh", "--help"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        missing = subprocess.run(
            ["bash", "scripts/launch-mobile.sh"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )

        self.assertIn("lai-gateway-mobile", help_result.stdout)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--candidate-ip is required", missing.stderr)
        self.assertNotIn("Bearer", help_result.stdout + help_result.stderr + missing.stdout + missing.stderr)


    def test_launch_local_checks_harness_then_serves_without_opening_browser(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_OPEN_BROWSER": "0",
                "PYTHON": sys.executable,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            port = free_port()
            proc = subprocess.Popen(
                ["bash", "scripts/launch-local.sh", "--bind", "127.0.0.1", "--port", str(port)],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert proc.stdout is not None
                self.assertEqual(proc.stdout.readline().strip(), "lai-gateway dev: ready")
                self.assertEqual(proc.stdout.readline().strip(), f"harness: {harness.url}")
                self.assertEqual(proc.stdout.readline().strip(), "access: loopback")
                self.assertEqual(proc.stdout.readline().strip(), f"ui: http://127.0.0.1:{port}/")
                self.assertEqual(
                    proc.stdout.readline().strip(),
                    f"lai-gateway listening on http://127.0.0.1:{port}",
                )
                with urlopen(Request(f"http://127.0.0.1:{port}/healthz"), timeout=5) as response:
                    self.assertEqual(response.status, 200)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.stderr is not None:
                    proc.stderr.close()

    def test_launch_local_blocks_when_harness_is_not_ready(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_OPEN_BROWSER": "0",
                "PYTHON": sys.executable,
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:9",
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            result = subprocess.run(
                ["bash", "scripts/launch-local.sh", "--bind", "127.0.0.1", "--port", "18788"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("overall: blocked", result.stderr)
            self.assertIn("harness_status", result.stderr)
            self.assertNotIn(TOKEN, result.stderr)


    def test_launch_model_help_and_key_guard_are_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        help_result = subprocess.run(
            ["bash", "scripts/launch-model.sh", "--help"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing-key"
            common_args = ["--host", "172.29.192.1", "--model-path", r"C:\Users\tester\models\code.gguf", "--model-name", "test-code-model"]
            plan = subprocess.run(
                ["bash", "scripts/launch-model.sh", *common_args, "--plan-only"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            missing = subprocess.run(
                ["bash", "scripts/launch-model.sh", *common_args, "--key-file", str(missing_path), "--probe-only"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
        self.assertIn("lai-gateway-model", help_result.stdout)
        self.assertIn("--smoke", help_result.stdout)
        self.assertIn("--record", help_result.stdout)
        self.assertIn("--eval", help_result.stdout)
        self.assertIn("--task", help_result.stdout)
        self.assertIn("--ephemeral", help_result.stdout)
        self.assertNotIn("Bearer", help_result.stdout + help_result.stderr + plan.stdout + plan.stderr + missing.stdout + missing.stderr)
        self.assertEqual(plan.returncode, 0)
        self.assertIn("lai-gateway-model: plan", plan.stdout)
        self.assertIn("--ctx-size 4096", plan.stdout)
        self.assertIn("key_file: /mnt/c/Users/tester/.config/lai-gateway/model-api-key", plan.stdout)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("model API key file is not ready", missing.stderr)

        incompatible = subprocess.run(
            ["bash", "scripts/launch-model.sh", "--foreground", "--ephemeral"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertEqual(incompatible.returncode, 2)
        self.assertIn("cannot be combined", incompatible.stderr)


    def test_launch_model_ephemeral_cleanup_is_scoped_to_started_process(self) -> None:
        repo = Path(__file__).parents[1]
        script = (repo / "scripts" / "launch-model.sh").read_text(encoding="utf-8")
        self.assertIn("cleanup_started_model", script)
        self.assertIn("trap cleanup_started_model EXIT INT TERM", script)
        self.assertIn('if [ "$ephemeral" = "1" ]; then', script)
        self.assertIn('kill "$pid" 2>/dev/null || true', script)
        self.assertIn("Get-NetTCPConnection -State Listen", script)
        self.assertIn("Stop-Process -Id $target", script)
        self.assertNotIn("Stop-Process -Name", script)
        self.assertNotIn("pkill", script)
        self.assertNotIn("taskkill", script.lower())


    def test_launch_model_reuses_ready_config_before_runtime_discovery(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "model-files-called"
            shim = root / "python-shim"
            shim.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [ \"${1:-}\" = \"-m\" ] && [ \"${2:-}\" = \"lai_gateway\" ] && [ \"${3:-}\" = \"model-status\" ]; then\n"
                "  case \" $* \" in *\" --json \"*) printf '%s\\n' '{\"overall\":\"ready\"}' ;; *) echo 'lai-gateway model-status: ready' ;; esac\n"
                "  exit 0\n"
                "fi\n"
                "if [ \"${1:-}\" = \"-m\" ] && [ \"${2:-}\" = \"lai_gateway\" ] && [ \"${3:-}\" = \"model-files\" ]; then\n"
                f"  touch '{marker}'\n"
                "  exit 91\n"
                "fi\n"
                "exec \"$REAL_PYTHON\" \"$@\"\n",
                encoding="utf-8",
            )
            shim.chmod(0o755)
            env = {**os.environ, "PYTHON": str(shim), "REAL_PYTHON": sys.executable}
            for name in (
                "LAI_GATEWAY_MODEL_HOST", "LAI_GATEWAY_MODEL_PORT",
                "LAI_GATEWAY_MODEL_PATH", "LAI_GATEWAY_MODEL_NAME",
                "LAI_GATEWAY_MODEL_API_KEY_FILE", "LAI_GATEWAY_MODEL_THREADS",
                "LAI_GATEWAY_MODEL_CTX_SIZE", "LAI_GATEWAY_MODEL_GPU_LAYERS",
            ):
                env.pop(name, None)
            result = subprocess.run(
                ["bash", "scripts/launch-model.sh", "--probe-only", "--ephemeral"],
                cwd=repo, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=10,
            )
            model_files_called = marker.exists()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reusing configured ready endpoint", result.stdout)
        self.assertIn("lai-gateway model-status: ready", result.stdout)
        self.assertFalse(model_files_called)


    def test_launch_model_does_not_put_bearer_key_in_shell_curl_arguments(self) -> None:
        repo = Path(__file__).parents[1]
        script = (repo / "scripts" / "launch-model.sh").read_text(encoding="utf-8")
        self.assertNotIn("curl -fsS -H", script)
        self.assertNotIn("Authorization: Bearer $(cat", script)
        self.assertIn("probe_models_endpoint", script)
        self.assertIn("model-smoke", script)
        self.assertIn("model_config_persisted: true", script)
        self.assertIn("stores_api_key_value: false", script)
        self.assertNotIn("Authorization: Bearer", script)


if __name__ == "__main__":
    unittest.main()
