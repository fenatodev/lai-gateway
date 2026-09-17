from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lai_gateway.local_operator_runtime import collect_local_operator_runtime
from lai_gateway.local_task_green_executor import _ALLOWED_EXACT_COMMANDS
from lai_gateway.local_task_approval_gate import collect_local_task_approval_gate


class LocalOperatorRuntimeTest(unittest.TestCase):
    def _collect(
        self,
        repo: Path,
        *,
        task_id: str = "operator-test",
        zone: str = "green",
        command: str = "git --version",
        execute: bool = False,
    ) -> dict[str, object]:
        return collect_local_operator_runtime(
            repo=repo,
            task_id=task_id,
            domain="dev",
            channel="chat",
            autonomy_zone=zone,
            capability="local.validation",
            intent="validate local operator runtime",
            allowed_paths=["lai_gateway/**", "tests/**"],
            validation_plan=[command],
            proposed_commands=[command],
            commands=[command],
            execute=execute,
        )

    def test_green_task_traverses_full_chain_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(Path(tmp))

        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(
            payload["stage_status"],
            {
                "file_pack": "written",
                "review": "ready",
                "approval": "ready_without_approval",
                "executor": "ready",
            },
        )
        self.assertFalse(payload["executes_commands"])
        self.assertTrue(payload["task_digest"].startswith("sha256:"))

    def test_green_task_can_execute_existing_allowlisted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(Path(tmp), execute=True)

        self.assertEqual(payload["overall"], "executed")
        self.assertTrue(payload["executes_commands"])
        self.assertEqual(payload["planned_commands"], ["git --version"])
        self.assertEqual(payload["command_results"][0]["status"], "success")

    def test_yellow_task_stops_before_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(Path(tmp), zone="yellow", execute=True)

        self.assertEqual(payload["overall"], "needs_approval")
        self.assertEqual(payload["stage_status"]["file_pack"], "written")
        self.assertEqual(payload["stage_status"]["review"], "ready")
        self.assertEqual(
            payload["stage_status"]["approval"],
            "needs_approval",
        )
        self.assertIsNone(payload["stage_status"]["executor"])
        self.assertFalse(payload["executes_commands"])
        self.assertEqual(payload["command_results"], [])

    def test_red_task_stops_before_review_and_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(Path(tmp), zone="red", execute=True)

        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["stage_status"]["file_pack"], "blocked")
        self.assertIsNone(payload["stage_status"]["review"])
        self.assertIsNone(payload["stage_status"]["approval"])
        self.assertIsNone(payload["stage_status"]["executor"])
        self.assertFalse(payload["executes_commands"])

    def test_non_allowlisted_command_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(
                Path(tmp),
                command="git log -1",
                execute=True,
            )

        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["stage_status"]["executor"], "blocked")
        self.assertFalse(payload["executes_commands"])
        self.assertEqual(payload["command_results"], [])

    def test_task_mutation_after_review_fails_content_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_path = repo / ".lai-ai/tasks/operator-mutation.task.json"

            def mutate_then_approve(**kwargs):
                approval = collect_local_task_approval_gate(**kwargs)
                task = json.loads(task_path.read_text(encoding="utf-8"))
                task["allowed_paths"].append("README.md")
                task_path.write_text(
                    json.dumps(task, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )
                return approval

            with patch(
                "lai_gateway.local_operator_runtime.collect_local_task_approval_gate",
                side_effect=mutate_then_approve,
            ):
                payload = self._collect(
                    repo,
                    task_id="operator-mutation",
                    execute=True,
                )

        self.assertEqual(payload["overall"], "invalid")
        self.assertEqual(payload["stage_status"]["executor"], "invalid")
        self.assertFalse(payload["executes_commands"])
        self.assertEqual(payload["command_results"], [])

    def test_malformed_approval_digest_executes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            def malformed_digest(**kwargs):
                approval = collect_local_task_approval_gate(**kwargs)
                approval["task_digest"] = "sha256:not-a-digest"
                return approval

            with patch(
                "lai_gateway.local_operator_runtime.collect_local_task_approval_gate",
                side_effect=malformed_digest,
            ):
                payload = self._collect(repo, execute=True)

        self.assertEqual(payload["overall"], "invalid")
        self.assertEqual(payload["stage_status"]["executor"], "invalid")
        self.assertFalse(payload["executes_commands"])
        self.assertEqual(payload["command_results"], [])

    def test_runtime_does_not_claim_new_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._collect(Path(tmp))

        security = payload["security"]
        self.assertFalse(security["operator_grants_authority"])
        self.assertFalse(security["effective_authorization"])
        self.assertFalse(security["issues_grants"])
        self.assertFalse(security["consumes_grants"])
        self.assertFalse(security["changes_autonomy_zone"])
        self.assertFalse(security["expands_executor_allowlist"])
        self.assertFalse(security["arbitrary_shell"])
        self.assertFalse(security["calls_harness"])
        self.assertFalse(security["dispatches_adapter"])
        self.assertFalse(security["executes_external_tools"])
        self.assertFalse(security["uses_credentials"])
        self.assertFalse(security["sends_messages"])
        self.assertFalse(security["publishes"])
        self.assertFalse(security["merges_main"])
        self.assertFalse(security["external_side_effects"])


    def test_pr127_exact_allowlist_is_unchanged(self) -> None:
        expected = (
            ("git", "--version"),
            ("git", "diff", "--check"),
            ("git", "status", "--short", "--branch"),
            ("git", "diff", "--stat"),
            ("python3", "-m", "compileall", "-q", "lai_gateway", "tests"),
            (
                "python3",
                "-m",
                "unittest",
                "tests.test_local_task_review_gate",
                "-v",
            ),
            (
                "python3",
                "-m",
                "unittest",
                "tests.test_local_task_approval_gate",
                "-v",
            ),
            (
                "python3",
                "-m",
                "unittest",
                "tests.test_local_task_green_executor",
                "-v",
            ),
            (
                "python3",
                "-m",
                "unittest",
                "tests.test_product_docs",
                "-v",
            ),
            ("make", "check"),
        )

        self.assertEqual(_ALLOWED_EXACT_COMMANDS, expected)


if __name__ == "__main__":
    unittest.main()
