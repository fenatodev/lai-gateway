from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "docs/product"


class DirectConversationDocsTest(unittest.TestCase):
    def test_current_product_docs_record_contract(self) -> None:
        for name in (
            "index.md",
            "implementation_matrix.md",
            "post_pr110_operating_plan.md",
            "alpha_readiness.md",
        ):
            content = (PRODUCT / name).read_text(
                encoding="utf-8"
            )

            self.assertIn(
                "direct-conversation-session/v1",
                content,
                msg=name,
            )

    def test_contract_preserves_architecture_boundaries(self) -> None:
        content = (
            (
                PRODUCT / "direct_conversation_session.md"
            ).read_text(encoding="utf-8")
            + "\n"
            + (
                PRODUCT
                / "pr_133_direct_conversation_session.md"
            ).read_text(encoding="utf-8")
        ).lower()

        for marker in (
            "dc-",
            "cs-*",
            "harness",
            "in memory",
            "8",
            "24,000",
            "authorization",
            "explicit",
        ):
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
