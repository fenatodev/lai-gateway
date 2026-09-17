from __future__ import annotations

import shlex
import unittest
from pathlib import Path

from lai_gateway.local_task_green_executor import _ALLOWED_EXACT_COMMANDS
from lai_gateway.workbench_local_operator import (
    WORKBENCH_LOCAL_OPERATOR_PROFILES,
    collect_workbench_local_operator,
    workbench_local_operator_profile_commands,
)


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchLocalOperatorTest(unittest.TestCase):
    def test_profiles_use_only_pr127_exact_allowlist(self) -> None:
        self.assertEqual(
            WORKBENCH_LOCAL_OPERATOR_PROFILES,
            (
                "status",
                "diff-check",
                "diff-stat",
                "compile",
                "gate-tests",
                "full-check",
            ),
        )

        for profile in WORKBENCH_LOCAL_OPERATOR_PROFILES:
            with self.subTest(profile=profile):
                commands = workbench_local_operator_profile_commands(profile)
                self.assertTrue(commands)
                for command in commands:
                    self.assertIn(
                        tuple(shlex.split(command)),
                        _ALLOWED_EXACT_COMMANDS,
                    )

    def test_each_profile_traverses_pr130_without_execution(self) -> None:
        for profile in WORKBENCH_LOCAL_OPERATOR_PROFILES:
            with self.subTest(profile=profile):
                payload = collect_workbench_local_operator(
                    repo=ROOT,
                    profile=profile,
                    execute=False,
                )

                self.assertEqual(payload["overall"], "ready")
                self.assertEqual(
                    payload["runtime"]["schema_version"],
                    "local-operator-runtime/v1",
                )
                self.assertEqual(
                    payload["runtime"]["stage_status"]["approval"],
                    "ready_without_approval",
                )
                self.assertEqual(
                    payload["runtime"]["stage_status"]["executor"],
                    "ready",
                )
                self.assertFalse(payload["executes_commands"])
                self.assertFalse(payload["security"]["calls_harness"])

    def test_status_profile_executes_through_existing_executor(self) -> None:
        payload = collect_workbench_local_operator(
            repo=ROOT,
            profile="status",
            execute=True,
        )

        self.assertEqual(payload["overall"], "executed")
        self.assertTrue(payload["executes_commands"])
        self.assertEqual(
            payload["runtime"]["planned_commands"],
            ["git status --short --branch"],
        )
        self.assertEqual(
            payload["runtime"]["command_results"][0]["status"],
            "success",
        )

    def test_unknown_profile_fails_closed(self) -> None:
        payload = collect_workbench_local_operator(
            repo=ROOT,
            profile="shell",
            execute=True,
        )

        self.assertEqual(payload["overall"], "invalid")
        self.assertIsNone(payload["runtime"])
        self.assertFalse(payload["executes_commands"])
        self.assertFalse(payload["security"]["arbitrary_command_input"])

    def test_profile_artifacts_use_ignored_state_root(self) -> None:
        payload = collect_workbench_local_operator(
            repo=ROOT,
            profile="status",
            execute=False,
        )

        file_pack = payload["runtime"]["stages"]["file_pack"]
        self.assertEqual(
            file_pack["output_root"],
            "state/local-operator",
        )


if __name__ == "__main__":
    unittest.main()
