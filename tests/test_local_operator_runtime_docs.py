from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "docs" / "product"


class LocalOperatorRuntimeDocsTest(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (PRODUCT / name).read_text(encoding="utf-8")

    def test_pr130_runtime_is_indexed_as_implemented(self) -> None:
        index = self._read("index.md")
        matrix = self._read("implementation_matrix.md")
        alpha = self._read("alpha_readiness.md")
        plan = self._read("post_pr110_operating_plan.md")

        for text in (index, matrix, alpha, plan):
            self.assertIn("local-operator-runtime/v1", text)

        self.assertIn("| local_operator_runtime | implemented |", matrix)
        self.assertIn("[PR130](pr_130_local_operator_runtime.md)", matrix)
        self.assertIn("sem ampliar allowlist", matrix)

    def test_pr130_docs_preserve_security_boundaries(self) -> None:
        runtime = self._read("local_operator_runtime.md")
        spec = self._read("pr_130_local_operator_runtime.md")
        combined = (runtime + "\n" + spec).lower()

        for marker in (
            "local-operator-runtime/v1",
            "ready_without_approval",
            "task_digest",
            "shell=false",
            "does not",
            "harness",
            "adapter",
            "credentials",
            "send messages",
            "publish",
            "merge `main`",
            "sudo",
        ):
            self.assertIn(marker, combined)


if __name__ == "__main__":
    unittest.main()
