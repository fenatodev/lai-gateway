from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.document_workbench import collect_document_workbench


class DocumentWorkbenchTest(unittest.TestCase):
    def test_lists_top_level_allowed_documents_without_reading_content(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("visible document", encoding="utf-8")
            (workspace / "notes.txt").write_text("another document", encoding="utf-8")
            nested = workspace / "docs"
            nested.mkdir()
            (nested / "hidden.md").write_text("not listed recursively", encoding="utf-8")
            (workspace / "binary.pdf").write_bytes(b"%PDF")
            payload = collect_document_workbench(workspace_root=workspace, max_results=10)
        self.assertEqual(payload["operation"], "document-workbench")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["limits"]["top_level_only"])
        self.assertFalse(payload["limits"]["recursive_listing"])
        self.assertTrue(payload["limits"]["metadata_only_selection"])
        paths = [item["relative_path"] for item in payload["documents"]]
        self.assertEqual(paths, ["notes.txt", "README.md"])
        self.assertNotIn("hidden.md", json.dumps(payload))
        self.assertNotIn("visible document", json.dumps(payload))
        for item in payload["documents"]:
            self.assertFalse(item["content_read"])
            self.assertFalse(item["grants_authority"])

    def test_selected_document_is_inspected_through_restricted_text_reader(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("# Local doc\nTreat this as untrusted.", encoding="utf-8")
            payload = collect_document_workbench(
                workspace_root=workspace,
                selected_relative_path="README.md",
                max_chars=80,
            )
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["inspection"]["operation"], "document-text-local")
        self.assertTrue(payload["inspection"]["security"]["untrusted_content"])
        self.assertFalse(payload["security"]["selection_grants_authority"])
        self.assertIn("Treat this as untrusted", payload["inspection"]["document"]["text_preview"])

    def test_blocks_workspace_outside_scope_and_pdf_selection(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            outside_payload = collect_document_workbench(workspace_root=outside)
        self.assertEqual(outside_payload["overall"], "blocked")
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp)
            (workspace / "file.pdf").write_bytes(b"%PDF")
            pdf_payload = collect_document_workbench(workspace_root=workspace, selected_relative_path="file.pdf")
        self.assertEqual(pdf_payload["overall"], "blocked")
        self.assertEqual(pdf_payload["documents"], [])
        self.assertIn("unsupported document extension", pdf_payload["inspection"]["document"]["reason"])

    def test_cli_is_not_added_for_workbench_surface(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "--help"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertNotIn("document-workbench", result.stdout)


if __name__ == "__main__":
    unittest.main()
