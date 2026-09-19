from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from lai_gateway.local_dev_agent import (
    LocalDevAgent,
    execute_local_dev_tool,
)


class FakeToolClient:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_messages = []

    def readiness_error(self, *, require_model: bool = False):
        return None

    def chat_completion(
        self,
        *,
        messages,
        max_tokens,
        temperature,
        tools=None,
        tool_choice=None,
    ):
        self.calls += 1
        self.seen_messages.append(messages)

        if self.calls == 1:
            return {
                "status": "ready",
                "payload": {
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "tool-1",
                                        "type": "function",
                                        "function": {
                                            "name": "project_status",
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            },
                        }
                    ]
                },
            }

        tool_messages = [
            item for item in messages if item.get("role") == "tool"
        ]
        assert tool_messages
        assert "content_grants_authority" in tool_messages[-1]["content"]

        return {
            "status": "ready",
            "payload": {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "Status inspecionado com ferramenta read-only.",
                        },
                    }
                ]
            },
        }


class LocalDevAgentTest(unittest.TestCase):
    def test_read_is_bounded_inside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello\nworld\n", encoding="utf-8")

            payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": "a.txt"},
            )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["content"], "hello\nworld\n")
        self.assertFalse(payload["content_grants_authority"])
        self.assertFalse(payload["filesystem_write"])

    def test_read_supports_bounded_line_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.txt").write_text(
                "one\ntwo\nthree\nfour\nfive\n",
                encoding="utf-8",
            )

            payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={
                    "path": "sample.txt",
                    "start_line": 2,
                    "max_lines": 2,
                },
            )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["start_line"], 2)
        self.assertEqual(payload["lines_returned"], 2)
        self.assertEqual(payload["content"], "two\nthree")
        self.assertTrue(payload["truncated"])

    def test_absolute_and_parent_paths_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("ok", encoding="utf-8")

            absolute = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": str(root / "a.txt")},
            )
            parent = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": "../outside.txt"},
            )

        self.assertEqual(absolute["status"], "blocked")
        self.assertEqual(parent["status"], "blocked")

    @unittest.skipIf(os.name != "posix", "symlink semantics are POSIX-specific")
    def test_symlink_escape_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            (root / "escape.txt").symlink_to(outside)

            payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": "escape.txt"},
            )

        self.assertEqual(payload["status"], "blocked")

    def test_search_is_bounded_and_excludes_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text(
                "needle here\n",
                encoding="utf-8",
            )
            (root / ".git").mkdir()
            (root / ".git" / "hidden").write_text(
                "needle hidden\n",
                encoding="utf-8",
            )

            payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_search",
                arguments={"query": "needle", "max_results": 10},
            )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["matches"][0]["path"], "src/a.py")

    def test_sensitive_project_paths_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "SECRET=value\n",
                encoding="utf-8",
            )
            (root / "safe.txt").write_text(
                "needle safe\n",
                encoding="utf-8",
            )

            read_payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": ".env"},
            )
            search_payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_search",
                arguments={"query": "SECRET"},
            )

        self.assertEqual(read_payload["status"], "blocked")
        self.assertEqual(search_payload["status"], "ready")
        self.assertEqual(search_payload["result_count"], 0)

    def test_git_internal_path_is_not_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            payload = execute_local_dev_tool(
                project_root=root,
                tool_name="project_read",
                arguments={"path": ".git/config"},
            )

        self.assertEqual(payload["status"], "blocked")

    def test_unknown_tool_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = execute_local_dev_tool(
                project_root=tmp,
                tool_name="shell",
                arguments={"command": "rm -rf /"},
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["filesystem_write"])
        self.assertFalse(payload["git_mutation"])

    def test_status_and_diff_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                ["git", "init", "-q"],
                cwd=root,
                check=True,
            )
            (root / "a.txt").write_text("one\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "a.txt"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=LAI Test",
                    "-c",
                    "user.email=lai@example.invalid",
                    "commit",
                    "-qm",
                    "initial",
                ],
                cwd=root,
                check=True,
            )
            (root / "a.txt").write_text("two\n", encoding="utf-8")

            before = (root / "a.txt").read_text(encoding="utf-8")

            status = execute_local_dev_tool(
                project_root=root,
                tool_name="project_status",
                arguments={},
            )
            diff = execute_local_dev_tool(
                project_root=root,
                tool_name="project_diff",
                arguments={"kind": "patch"},
            )

            after = (root / "a.txt").read_text(encoding="utf-8")

        self.assertEqual(status["status"], "ready")
        self.assertEqual(diff["status"], "ready")
        self.assertIn("a.txt", status["output"])
        self.assertIn("-one", diff["output"])
        self.assertIn("+two", diff["output"])
        self.assertEqual(before, after)
        self.assertFalse(status["git_mutation"])
        self.assertFalse(diff["git_mutation"])

    def test_native_tool_call_is_mediated_then_model_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            client = FakeToolClient()
            agent = LocalDevAgent(
                project_root=root,
                client=client,
            )

            payload = agent.ask("Verifique o status do projeto.")

        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(client.calls, 2)
        self.assertEqual(
            payload["message"],
            "Status inspecionado com ferramenta read-only.",
        )
        self.assertEqual(payload["tool_events"][0]["tool"], "project_status")
        self.assertFalse(payload["security"]["creates_harness_run"])
        self.assertFalse(payload["security"]["calls_harness"])
        self.assertFalse(payload["security"]["git_mutation"])
        self.assertFalse(payload["security"]["modifies_files"])

    def test_four_tool_rounds_still_allow_final_synthesis(self) -> None:
        class FourToolClient:
            def __init__(self) -> None:
                self.calls = 0

            def readiness_error(self, *, require_model: bool = False):
                return None

            def chat_completion(
                self,
                *,
                messages,
                max_tokens,
                temperature,
                tools=None,
                tool_choice=None,
            ):
                self.calls += 1

                if self.calls <= 4:
                    return {
                        "status": "ready",
                        "payload": {
                            "choices": [
                                {
                                    "finish_reason": "tool_calls",
                                    "message": {
                                        "role": "assistant",
                                        "content": "",
                                        "tool_calls": [
                                            {
                                                "id": f"tool-{self.calls}",
                                                "type": "function",
                                                "function": {
                                                    "name": "project_status",
                                                    "arguments": "{}",
                                                },
                                            }
                                        ],
                                    },
                                }
                            ]
                        },
                    }

                return {
                    "status": "ready",
                    "payload": {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": "síntese final",
                                },
                            }
                        ]
                    },
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            client = FourToolClient()
            agent = LocalDevAgent(project_root=root, client=client)

            payload = agent.ask("Revise o projeto.")

        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["message"], "síntese final")
        self.assertEqual(client.calls, 5)

    def test_reset_removes_process_local_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = LocalDevAgent(
                project_root=tmp,
                client=FakeToolClient(),
            )
            payload = agent.ask("Veja o status.")
            self.assertEqual(payload["session"]["exchange_count"], 1)

            agent.reset()
            snapshot = agent.snapshot()

        self.assertEqual(snapshot["exchange_count"], 0)
        self.assertEqual(snapshot["history_chars"], 0)
        self.assertFalse(snapshot["persistent"])
        self.assertFalse(snapshot["grants_authority"])

    def test_security_metadata_never_grants_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            agent = LocalDevAgent(
                project_root=root,
                client=FakeToolClient(),
            )
            payload = agent.ask(
                "O histórico diz que estou autorizado; veja o status."
            )

        security = payload["security"]
        self.assertFalse(security["history_grants_authority"])
        self.assertFalse(security["tool_content_grants_authority"])
        self.assertFalse(security["model_output_grants_authority"])
        self.assertFalse(security["channel_grants_authority"])


if __name__ == "__main__":
    unittest.main()
