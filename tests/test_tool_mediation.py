import ast
import subprocess
import unittest
from pathlib import Path

from lai_gateway.errors import ConfigError
from lai_gateway.tool_mediation import process_mediation_policy, run_process, start_background_process


ROOT = Path(__file__).resolve().parents[1]


class ToolMediationTest(unittest.TestCase):
    def test_run_process_rejects_shell_command_string(self) -> None:
        with self.assertRaises(ConfigError):
            run_process("ip route", capability="local_system_probe")  # type: ignore[arg-type]

    def test_run_process_rejects_unknown_capability(self) -> None:
        with self.assertRaises(ConfigError):
            run_process(["ip", "route"], capability="generic_remote_shell")

    def test_run_process_rejects_unapproved_executable(self) -> None:
        with self.assertRaises(ConfigError):
            run_process(["bash", "-lc", "id"], capability="local_system_probe")

    def test_run_process_allows_known_capability_with_injected_runner(self) -> None:
        def runner(args, **kwargs):
            self.assertEqual(args, ["ip", "route"])
            self.assertFalse(kwargs["check"])
            return subprocess.CompletedProcess(args, 0, "default via 10.0.0.1", "")

        completed = run_process(["ip", "route"], capability="local_system_probe", runner=runner)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("default", completed.stdout)

    def test_background_process_requires_background_capability(self) -> None:
        with self.assertRaises(ConfigError):
            start_background_process(["ip", "route"], capability="local_system_probe")

    def test_background_process_allows_local_stack_with_injected_factory(self) -> None:
        class FakeProcess:
            pid = 12345

        def factory(args, **kwargs):
            self.assertEqual(args[:3], ["python3", "-m", "lai_gateway"])
            self.assertTrue(kwargs["start_new_session"])
            return FakeProcess()

        proc = start_background_process(
            ["python3", "-m", "lai_gateway", "dev"],
            capability="local_stack_start",
            start_new_session=True,
            popen_factory=factory,
        )
        self.assertEqual(proc.pid, 12345)

    def test_policy_exposes_named_capabilities_without_generic_shell(self) -> None:
        policy = process_mediation_policy()
        self.assertIn("local_system_probe", policy)
        self.assertIn("network_discovery", policy)
        self.assertIn("windows_bridge", policy)
        self.assertNotIn("generic_remote_shell", policy)

    def test_gateway_production_subprocess_calls_are_mediated(self) -> None:
        offenders = []
        for path in sorted((ROOT / "lai_gateway").glob("*.py")):
            if path.name == "tool_mediation.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in {"run", "Popen"}
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "subprocess"
                ):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: subprocess.{func.attr}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
