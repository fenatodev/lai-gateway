import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.memory_context import collect_memory_context, render_memory_context

ROOT = Path(__file__).resolve().parents[1]
SECRET = "token=abcdefghi123456789"


class MemoryContextTest(unittest.TestCase):
    def test_remember_and_show_are_project_scoped_without_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            written = collect_memory_context(
                memory_action="remember",
                context_kind="project",
                project_id="alpha",
                note="Preferir nomes de arquivos em minúsculas.",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            alpha = collect_memory_context(
                memory_action="show",
                context_kind="project",
                project_id="alpha",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            beta = collect_memory_context(
                memory_action="show",
                context_kind="project",
                project_id="beta",
                memory_dir=tmp,
                scope_root=ROOT,
            )
        text = json.dumps(alpha, sort_keys=True) + render_memory_context(alpha)
        self.assertEqual(written["status"], "written")
        self.assertTrue(written["persisted"])
        self.assertEqual(alpha["entry_count"], 1)
        self.assertEqual(beta["entry_count"], 0)
        self.assertIn("Preferir nomes", text)
        self.assertFalse(alpha["security"]["memory_grants_authority"])
        self.assertFalse(alpha["security"]["approval_from_memory"])
        self.assertFalse(alpha["security"]["grants_permission"])
        self.assertFalse(alpha["security"]["executes_tools"])

    def test_personal_and_project_contexts_are_separate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            collect_memory_context(
                memory_action="remember",
                context_kind="personal",
                project_id="personal",
                note="Responder em pt-BR.",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            personal = collect_memory_context(
                memory_action="show",
                context_kind="personal",
                project_id="personal",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            project = collect_memory_context(
                memory_action="show",
                context_kind="project",
                project_id="personal",
                memory_dir=tmp,
                scope_root=ROOT,
            )
        self.assertEqual(personal["entry_count"], 1)
        self.assertEqual(project["entry_count"], 0)
        self.assertEqual(personal["entries"][0]["context_kind"], "personal")

    def test_secret_shaped_content_is_rejected_and_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            payload = collect_memory_context(
                memory_action="remember",
                context_kind="project",
                project_id="alpha",
                note=SECRET,
                memory_dir=tmp,
                scope_root=ROOT,
            )
            raw = "\n".join(path.read_text(encoding="utf-8") for path in Path(tmp).rglob("*.jsonl")) if list(Path(tmp).rglob("*.jsonl")) else ""
        rendered = json.dumps(payload, sort_keys=True) + render_memory_context(payload)
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["persisted"])
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn(SECRET, raw)

    def test_forget_appends_tombstone_without_rewriting_store(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            written = collect_memory_context(
                memory_action="remember",
                context_kind="project",
                project_id="alpha",
                note="Contexto temporário.",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            forgotten = collect_memory_context(
                memory_action="forget",
                context_kind="project",
                project_id="alpha",
                memory_id=written["memory_id"],
                memory_dir=tmp,
                scope_root=ROOT,
            )
            shown = collect_memory_context(
                memory_action="show",
                context_kind="project",
                project_id="alpha",
                memory_dir=tmp,
                scope_root=ROOT,
            )
            raw_events = [json.loads(line) for path in Path(tmp).rglob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(forgotten["status"], "forgotten")
        self.assertEqual(shown["entry_count"], 0)
        self.assertEqual([event["event_type"] for event in raw_events], ["remembered", "forgotten"])

    def test_rejects_path_traversal_and_out_of_scope_memory_dir(self) -> None:
        bad_project = collect_memory_context(memory_action="show", project_id="../x", scope_root=ROOT)
        bad_dir = collect_memory_context(memory_action="show", memory_dir="/tmp/lai-memory-outside", scope_root=ROOT)
        self.assertEqual(bad_project["overall"], "blocked")
        self.assertEqual(bad_dir["overall"], "blocked")

    def test_cli_memory_context_is_local_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "memory-context",
                    "--memory-action",
                    "remember",
                    "--context-kind",
                    "project",
                    "--project-id",
                    "alpha",
                    "--note",
                    "Manter revisão curta antes de código funcional.",
                    "--memory-dir",
                    tmp,
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "memory-context")
        self.assertEqual(payload["status"], "written")
        self.assertFalse(payload["security"]["memory_grants_authority"])
        self.assertFalse(payload["security"]["network_calls"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
