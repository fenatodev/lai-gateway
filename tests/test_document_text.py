import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.document_text import collect_document_text_local, render_document_text_local


class DocumentTextLocalTest(unittest.TestCase):
    def test_extracts_allowed_markdown_inside_workspace_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "note.md").write_text("# Título\nConteúdo local não confiável.\n", encoding="utf-8")
            payload = collect_document_text_local(
                workspace_root=workspace,
                relative_path="note.md",
                max_chars=200,
                scope_root=root,
            )
        rendered = render_document_text_local(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "document-text-local")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["document"]["schema_version"], "document-text-local/v1")
        self.assertIn("Conteúdo local", payload["document"]["text_preview"])
        self.assertTrue(payload["document"]["untrusted_content"])
        self.assertFalse(payload["security"]["grants_permission"])
        self.assertFalse(payload["security"]["grants_authority"])
        self.assertFalse(payload["security"]["approval_inferred"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["network_access"])
        self.assertFalse(payload["security"]["scans_home"])
        self.assertNotIn("Bearer", text)

    def test_rejects_pdf_office_binary_and_ocr_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            for name in ("paper.pdf", "doc.docx", "sheet.xlsx", "image.png"):
                (workspace / name).write_bytes(b"not text")
                payload = collect_document_text_local(workspace_root=workspace, relative_path=name, scope_root=root)
                with self.subTest(name=name):
                    self.assertEqual(payload["overall"], "blocked")
                    self.assertFalse(payload["security"]["supports_pdf"])
                    self.assertFalse(payload["security"]["supports_ocr"])
                    self.assertFalse(payload["security"]["supports_office"])
                    self.assertEqual(payload["document"]["text_preview"], "")

    def test_rejects_traversal_absolute_paths_and_out_of_scope_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "ok.txt").write_text("ok", encoding="utf-8")
            outside_file = Path(outside) / "outside.txt"
            outside_file.write_text("outside", encoding="utf-8")
            cases = [
                {"workspace_root": workspace, "relative_path": "../outside.txt"},
                {"workspace_root": workspace, "relative_path": str(outside_file)},
                {"workspace_root": outside, "relative_path": "outside.txt"},
            ]
            for case in cases:
                payload = collect_document_text_local(scope_root=root, **case)
                self.assertEqual(payload["overall"], "blocked")
                self.assertEqual(payload["document"]["text_preview"], "")
                self.assertFalse(payload["security"]["filesystem_write"])

    def test_rejects_symlink_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / "target.txt"
            target.write_text("target", encoding="utf-8")
            link = workspace / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink unavailable")
            payload = collect_document_text_local(workspace_root=workspace, relative_path="link.txt", scope_root=root)
        self.assertEqual(payload["overall"], "blocked")
        self.assertIn("symlink", payload["document"]["reason"])

    def test_rejects_secret_shaped_text_and_truncates_large_allowed_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "secret.txt").write_text("api_key=supersecretvalue123456", encoding="utf-8")
            (workspace / "long.txt").write_text("a" * 200, encoding="utf-8")
            blocked = collect_document_text_local(workspace_root=workspace, relative_path="secret.txt", scope_root=root)
            ready = collect_document_text_local(workspace_root=workspace, relative_path="long.txt", max_chars=25, scope_root=root)
        self.assertEqual(blocked["overall"], "blocked")
        self.assertEqual(blocked["document"]["text_preview"], "")
        self.assertEqual(ready["overall"], "ready")
        self.assertEqual(len(ready["document"]["text_preview"]), 25)
        self.assertTrue(ready["document"]["text_truncated"])

    def test_cli_document_text_local_json_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "note.json").write_text('{"status":"ok"}', encoding="utf-8")
            env = dict(os.environ)
            env["LAI_GATEWAY_TOKEN_FILE"] = str(root / "missing-token")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "document-text-local",
                    "--workspace-root",
                    str(workspace),
                    "--relative-path",
                    "note.json",
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["overall"], "ready")
        self.assertIn("status", payload["document"]["text_preview"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
