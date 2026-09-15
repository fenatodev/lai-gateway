import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DOCS = ROOT / "docs" / "product"


class ProductDocsTest(unittest.TestCase):
    def test_post_pr88_roadmap_artifacts_exist(self) -> None:
        for name in (
            "roadmap.md",
            "implementation_matrix.md",
            "alpha_readiness.md",
            "roadmap_review_prompt.md",
            "pr_89_roadmap_alpha_readiness.md",
        ):
            path = PRODUCT_DOCS / name
            self.assertTrue(path.exists(), name)
            self.assertGreater(len(path.read_text(encoding="utf-8")), 200, name)

    def test_roadmap_preserves_lai_architecture_dimensions(self) -> None:
        text = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        for term in ("domínio", "canal", "autonomia", "capacidade"):
            self.assertIn(term, text)
        self.assertIn("GPT-6, Codex e Astra", text)
        self.assertIn("não são autoridade automática", text)

    def test_matrix_distinguishes_contract_from_implemented(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        self.assertIn("browser | contract", text)
        self.assertIn("n8n | contract", text)
        self.assertIn("voice | contract", text)
        self.assertIn("local_status adapter | experimental", text)
        self.assertIn("instalação pública | planned", text)

    def test_alpha_readiness_blocks_overclaiming(self) -> None:
        text = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        for forbidden_claim in (
            "browser agent completo",
            "automação n8n real",
            "voz operacional",
            "MCP tool execution generalizado",
        ):
            self.assertIn(forbidden_claim, text)
        self.assertIn("Ainda não está apto a ser chamado de produto completo", text)


if __name__ == "__main__":
    unittest.main()
