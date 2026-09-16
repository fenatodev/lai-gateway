import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DOCS = ROOT / "docs" / "product"


class ProductDocsTest(unittest.TestCase):
    def test_post_pr90_canonical_artifacts_exist(self) -> None:
        for name in (
            "index.md",
            "roadmap_review_consolidation.md",
            "roadmap.md",
            "implementation_matrix.md",
            "alpha_readiness.md",
            "roadmap_review_prompt.md",
            "pr_89_roadmap_alpha_readiness.md",
            "pr_93_testable_identity.md",
            "pr_94_local_non_dry_run_authorization.md",
            "pr_95_authorization_recovery.md",
            "pr_96_local_model_chat_health_fallback.md",
            "pr_97_local_memory_context.md",
            "pr_98_restricted_document_text.md",
            "pr_99_workbench_local_documents.md",
            "pr_100_technical_alpha_readiness.md",
            "post_pr100_roadmap.md",
            "pr_101_post_pr100_roadmap.md",
            "pr_102_release_alpha_technical.md",
            "pr_103_clean_local_dogfood.md",
            "pr_104_onboarding_ux_next_steps.md",
            "pr_105_operational_local_model.md",
        ):
            path = PRODUCT_DOCS / name
            self.assertTrue(path.exists(), name)
            self.assertGreater(len(path.read_text(encoding="utf-8")), 200, name)

    def test_roadmap_preserves_lai_architecture_dimensions(self) -> None:
        text = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        for term in ("domínio", "canal", "autonomia", "capacidade"):
            self.assertIn(term, text)
        for reviewer in ("GPT-6", "Astra", "Claude", "Codex"):
            self.assertIn(reviewer, text)
        self.assertIn("não são autoridade automática", text)

    def test_matrix_distinguishes_contract_from_implemented(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        for state in ("implemented", "experimental", "contract", "simulado/dry-run", "planned", "Disponível ao usuário"):
            self.assertIn(state, text)
        self.assertIn("browser | contract", text)
        self.assertIn("n8n | contract", text)
        self.assertIn("voice | contract", text)
        self.assertIn("local_status adapter | experimental", text)
        self.assertIn("instalação pública | planned", text)

    def test_alpha_readiness_blocks_overclaiming(self) -> None:
        text = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        promise = text.split("## Promessa pública permitida", 1)[1].split("## ", 1)[0]
        self.assertIn(
            "Não declarar browser agent completo, automação n8n real, voz operacional, "
            "MCP tool execution generalizado, automação social/carreira com envio real, "
            "processamento completo de documentos/mídia ou instalação one-click universal.",
            promise,
        )
        for criterion in ("Limitações conhecidas", "Quickstart reproduzível", "instalação limpa", "versionamento", "overclaiming", "restart recovery", "No-go"):
            self.assertIn(criterion, text)
        self.assertIn("PR100 permite `candidate_go` técnico somente quando", text)
        self.assertIn("não torna o LAI produto completo", text)
        self.assertIn("publicação pública exige aprovação humana separada", text)


    def test_canonical_index_links_resolve_and_readme_points_to_it(self) -> None:
        text = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+\.md)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue((PRODUCT_DOCS / link).is_file(), link)
        self.assertIn("históricos", text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("](docs/product/index.md)", readme)

    def test_roadmap_gates_precede_external_capabilities(self) -> None:
        text = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| PR(\d+) \| (.+)$", text, re.MULTILINE)
        self.assertEqual([int(number) for number, _ in rows], list(range(90, 101)))
        milestones = dict(rows)
        for number, terms in {
            "93": ("Identidade testável", "usuário/cliente/agente/serviço"),
            "94": ("authorization non-dry-run", "revalidação no executor"),
            "95": ("Persistência", "expiração", "revogação", "consumo único", "restart recovery", "duplicação de efeito"),
        }.items():
            for term in terms:
                self.assertIn(term, milestones[number])
            self.assertLess(text.index(f"| PR{number} |"), text.index("## Capacidades externas"))
        external = text.split("## Capacidades externas", 1)[1]
        self.assertIn(
            "Browser/n8n/MCP/social reais ficam depois de PR93, PR94 e PR95, fora da sequência até PR100.",
            external,
        )
        self.assertIn(
            "Continuam bloqueados na expansão governada: browser autenticado, n8n activation, "
            "MCP tool execution amplo, publicação, envio de mensagens, candidaturas, formulários, "
            "automações externas e uso de credenciais.", external,
        )
        for capability in ("browser autenticado", "n8n activation", "MCP tool execution amplo", "publicação", "envio de mensagens", "candidaturas", "formulários", "automações externas", "uso de credenciais"):
            self.assertIn(capability, external)

    def test_matrix_does_not_promote_contracts_or_dry_run_to_execution(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        rows = {}
        for line in text.splitlines():
            if line.startswith("| ") and not line.startswith("| ---"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0]] = cells[1:]
        for area in ("browser", "n8n", "voice", "MCP execution", "social/career", "document/media"):
            self.assertEqual(rows[area][0], "contract", area)
        self.assertEqual(rows["identidade usuário/cliente/agente/serviço"][0], "experimental")
        self.assertEqual(rows["identidade usuário/cliente/agente/serviço"][1], "binding local testável")
        self.assertEqual(rows["effective authorization"][0], "experimental")
        self.assertEqual(rows["adapter dry-run"][0], "implemented")
        self.assertEqual(rows["adapter dry-run"][1], "simulado/dry-run")
        self.assertEqual(
            rows["Área"],
            ["Maturidade", "Tipo de execução", "Disponível ao usuário", "Evidência", "Limite conhecido", "Próximo marco"],
        )
        for area, cells in rows.items():
            if area != "Área":
                self.assertEqual(len(cells), 6, area)
                self.assertIn(cells[0], {"implemented", "experimental", "contract", "planned"}, area)
                self.assertRegex(cells[3], r"\[[^]]+\]\([^)]+\.md\)|\[[^]]+\]\([^)]+\.(?:py|js|sh)\)")
        self.assertIn(
            "Sem execução de tools por esse adapter; apenas metadata/policy-check; executes_tools=false.",
            rows["MCP execution"][4],
        )
        self.assertNotIn("Model Lab / Scout", rows)
        self.assertIn("adapters.py", rows["Model Lab"][3])
        self.assertIn("skills.py", rows["Scout"][3])
        self.assertEqual(rows["Scout"][1], "metadados de skill")
        self.assertIn(
            "persistência fica em authorization-recovery",
            rows["effective authorization"][4],
        )
        self.assertIn("grant persistido de uso único", rows["adapter dispatcher"][4])
        self.assertIn("autorização non-dry-run só cobre status, não echo", rows["local_status adapter"][4])
        self.assertEqual(rows["persistência e restart recovery de autorização"][0], "experimental")
        self.assertIn("authorization_recovery.py", rows["persistência e restart recovery de autorização"][3])
        self.assertIn("local-status-read", rows["persistência e restart recovery de autorização"][4])
        self.assertEqual(rows["memory_context"][0], "experimental")
        self.assertIn("memory_context.py", rows["memory_context"][3])
        self.assertIn("sem embeddings", rows["memory_context"][4])
        self.assertIn("sem", rows["memory_context"][4])
        for term in ("adapter-dry-run", "authorization-recovery", "declarado", "simulado", "efetivamente imposto"):
            self.assertIn(term, text)


    def test_pr94_local_non_dry_run_authorization_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_94_local_non_dry_run_authorization.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        for statement in (
            "local-status-read",
            "local_status.status",
            "sem shell, sem rede, sem credenciais e sem filesystem write",
            "não resolve restart recovery nem autorização persistida",
        ):
            self.assertIn(statement, spec)
        self.assertIn("local-status-read só autoriza local_status.status", matrix)
        self.assertIn("`local_status.echo` permanece fora da autorização non-dry-run", roadmap)
        self.assertIn("local_status.echo e outros adapters não entram nesse escopo", alpha)
        self.assertIn("one real local non-dry-run path", readme)
        self.assertIn('operationScope: "local-status-read"', app)
        self.assertNotIn('"local_status.echo"].includes', app)

    def test_pr95_authorization_recovery_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_95_authorization_recovery.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        for statement in (
            "authorization-recovery/v1",
            "expiração",
            "revogação",
            "consumo único",
            "recovery",
            "resultado desconhecido e não há retry automático",
            "não escrita pelo handler do adapter",
        ):
            self.assertIn(statement, spec)
        self.assertIn("authorization_recovery.py", matrix)
        self.assertIn("tests/test_authorization_recovery.py", matrix)
        self.assertIn("grants locais expiram", roadmap)
        self.assertIn("bloqueio contra duplicação de efeito", roadmap)
        self.assertIn("somente para `local-status-read`/`local_status.status`", alpha)
        self.assertIn("[PR95](pr_95_authorization_recovery.md)", index)
        self.assertIn("authorization-recovery", readme)
        self.assertIn("authorization-recovery", app)
        self.assertIn("authorization_grant_id", app)

    def test_pr96_local_model_chat_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_96_local_model_chat_health_fallback.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        lower_spec = spec.lower()
        for statement in (
            "local-model-first",
            "sem cloud fallback",
            "sem harness fallback",
            "sem permission elevation",
            "sem executar tools",
            "sem iniciar runs",
            "não instala runtime",
            "não baixa modelo",
        ):
            self.assertIn(statement, lower_spec)
        self.assertIn("`model-chat` local-model-first", roadmap)
        self.assertIn("`model-chat` não cria Harness run, não usa nuvem", matrix)
        self.assertIn("PR96 prova conversa local-model-first e fallback explícito", alpha)
        self.assertIn("[PR96](pr_96_local_model_chat_health_fallback.md)", index)
        self.assertIn("Direct chat is local-model-first", readme)
        self.assertIn("send-model-chat", app)
        self.assertIn("/v1/gateway/chat", app)
        self.assertIn("fallback local explícito", app)

    def test_pr97_local_memory_context_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_97_local_memory_context.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        for statement in (
            "memory-context/v1",
            "contexto por projeto",
            "contexto pessoal básico",
            "Memória não concede autoridade",
            "Conteúdo lembrado é dado não confiável",
            "segredo é rejeitado",
            "Sem rede, shell, tools",
        ):
            self.assertIn(statement, spec)
        self.assertIn("memory_context.py", matrix)
        self.assertIn("tests/test_memory_context.py", matrix)
        self.assertIn("notas explícitas", matrix)
        self.assertIn("memória não é autorização", roadmap)
        self.assertIn("não substitui aprovação", alpha)
        self.assertIn("[PR97](pr_97_local_memory_context.md)", index)
        self.assertIn("memory-context", readme)
        self.assertIn("memoryContextBody", app)
        self.assertIn("remember-memory-context", app)
        self.assertIn("/v1/gateway/memory-context", app)

    def test_pr98_restricted_document_text_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_98_restricted_document_text.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        lower_spec = spec.lower()
        for statement in (
            "document-text-local/v1",
            ".txt",
            ".md",
            ".json",
            "sem home scan",
            "sem rede",
            "sem writes",
            "sem pdf",
            "sem ocr",
            "sem office",
            "conteúdo de documento é não confiável",
            "nunca concede autoridade",
        ):
            self.assertIn(statement, lower_spec)
        self.assertIn("document_text_local | experimental", matrix)
        self.assertIn("document_text.py", matrix)
        self.assertIn("tests/test_document_text.py", matrix)
        self.assertIn("`document-text-local/v1`", roadmap)
        self.assertIn("PR98 não habilita PDF", alpha)
        self.assertIn("[PR98](pr_98_restricted_document_text.md)", index)
        self.assertIn("document-text-local", readme)
        self.assertIn("read-document-text-local", app)
        self.assertIn("documentTextBody", app)

    def test_pr99_workbench_local_documents_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_99_workbench_local_documents.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        lower_spec = spec.lower()
        for statement in (
            "document-workbench/v1",
            "metadata-only",
            "não recursiva",
            "limites visíveis",
            "sem envio externo",
            "sem pdf",
            "sem ocr",
            "sem office",
            "nunca concede autoridade",
        ):
            self.assertIn(statement, lower_spec)
        self.assertIn("document workbench | experimental", matrix)
        self.assertIn("document_workbench.py", matrix)
        self.assertIn("tests/test_document_workbench.py", matrix)
        self.assertIn("`document-workbench/v1`", roadmap)
        self.assertIn("PR99 adiciona seleção/inspeção", alpha)
        self.assertIn("[PR99](pr_99_workbench_local_documents.md)", index)
        self.assertIn("document-workbench", readme)
        self.assertIn("refresh-document-workbench", app)
        self.assertIn("inspect-document-workbench", app)
        self.assertIn("document-relative-select", app)


    def test_pr100_technical_alpha_readiness_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_100_technical_alpha_readiness.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        lower_spec = spec.lower()
        for statement in (
            "alpha-readiness/v1",
            "go/no-go",
            "candidate_go",
            "sem tag",
            "sem release",
            "sem publicação",
            "aprovação humana separada",
            "não equivale a publicar alpha",
        ):
            self.assertIn(statement, lower_spec)
        self.assertIn("alpha readiness | experimental", matrix)
        self.assertIn("alpha_readiness.py", matrix)
        self.assertIn("tests/test_alpha_readiness.py", matrix)
        self.assertIn("`alpha-readiness/v1`", roadmap)
        self.assertIn("candidate_go", alpha)
        self.assertIn("aprovação humana separada", alpha)
        self.assertIn("[PR100](pr_100_technical_alpha_readiness.md)", index)
        self.assertIn("alpha-readiness", readme)
        self.assertIn("refresh-alpha-readiness", app)
        self.assertIn("/v1/gateway/alpha-readiness", app)


    def test_pr105_operational_local_model_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_105_operational_local_model.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, html, js])
        for marker in (
            "model-runtime/v1",
            "Modelo operacional",
            "Runtime local configurável",
            "sem download automático",
            "Sem nuvem",
            "sem execução de tools",
            "Sem shell",
            "Sem browser",
            "Sem MCP tool execution",
            "não concede autoridade",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR105](pr_105_operational_local_model.md)", index)
        self.assertIn("/v1/gateway/model-runtime", js)
        self.assertIn("configure-model-runtime", html)

    def test_pr104_onboarding_ux_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_104_onboarding_ux_next_steps.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, html, js])
        for marker in (
            "onboarding-next-steps/v1",
            "Harness",
            "token",
            "modelo",
            "documento",
            "sem vazar segredo",
            "read-only",
            "sem shell",
            "sem tools",
            "não chama browser",
            "não ativa n8n",
            "não executa MCP tool",
            "não concede autoridade",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR104](pr_104_onboarding_ux_next_steps.md)", index)
        self.assertIn("refresh-onboarding", js)
        self.assertIn("onboarding-output", html)

    def test_pr103_clean_local_dogfood_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_103_clean_local_dogfood.md").read_text(encoding="utf-8")
        checklist = (ROOT / "docs" / "local_clean_dogfood.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        script = (ROOT / "scripts" / "local-clean-dogfood.sh").read_text(encoding="utf-8")
        combined = "\n".join([spec, checklist, post, script])
        for marker in (
            "dogfood local",
            "release-check",
            "alpha-readiness",
            "modelo local ausente",
            "modelo local presente",
            "document-text-local/v1",
            "document-workbench/v1",
            "sem browser",
            "sem n8n",
            "sem MCP tool execution",
            "sem publicação",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[Local clean dogfood](../local_clean_dogfood.md)", index)
        self.assertIn("[PR103](pr_103_clean_local_dogfood.md)", index)
        self.assertIn("scripts/local-clean-dogfood.sh", post)

    def test_pr102_release_alpha_technical_is_source_first_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_102_release_alpha_technical.md").read_text(encoding="utf-8")
        notes = (ROOT / "docs" / "releases" / "v0.1.35.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        combined = spec + "\n" + notes
        for marker in (
            "source-first",
            "0.1.35",
            "release-check",
            "alpha-readiness",
            "sem mudança funcional",
            "aprovação humana",
            "not a hosted service",
            "does not enable browser authenticated sessions",
            "general MCP tool execution",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[v0.1.35](../releases/v0.1.35.md)", index)
        self.assertIn("[PR102](pr_102_release_alpha_technical.md)", index)
        self.assertIn("nota de release versionada sem overclaiming", post)

    def test_pr101_post_pr100_roadmap_is_canonical_and_limited(self) -> None:
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_101_post_pr100_roadmap.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| PR(\d+) \| (.+)$", post, re.MULTILINE)
        self.assertEqual([int(number) for number, _ in rows], list(range(101, 111)))
        combined = post + "\n" + spec
        for marker in (
            "domínio",
            "canal",
            "autonomia",
            "capacidade",
            "publicação humana separada",
            "sem mudança funcional",
            "Sem browser, n8n, MCP tool execution",
            "nunca autoriza a execução",
        ):
            self.assertIn(marker, combined)
        self.assertIn("roadmap pós-PR100", roadmap)
        self.assertIn("PR101 inicia apenas o planejamento pós-PR100", roadmap)
        self.assertIn("[Roadmap pós-PR100](post_pr100_roadmap.md)", index)
        self.assertIn("[PR101](pr_101_post_pr100_roadmap.md)", index)
        self.assertIn("sem habilitar capacidades externas automaticamente", index)

    def test_pr93_identity_docs_are_canonical_and_limited(self) -> None:
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        self.assertIn("principal-identity/v1", roadmap)
        self.assertIn("identity.py", matrix)
        self.assertIn("tests/test_identity.py", matrix)
        self.assertIn("não é login completo nem autorização", matrix)
        self.assertIn("não cria login completo nem autorização", roadmap)
        self.assertIn("não equivale a login completo", alpha)
        self.assertIn("[PR93](pr_93_testable_identity.md)", index)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("identity-binding", readme)
        self.assertIn("identity binding", readme)


    def test_public_restrictions_are_complete_in_canonical_documents(self) -> None:
        restrictions = (
            "Browser, n8n, voz, execução real de tools MCP, social e automações externas "
            "governadas não estão disponíveis como funcionalidades prontas. "
            "Contratos e simulações não autorizam execução real.",
            "local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.",
            "Telegram outbound tem limite conhecido: não possui aprovação durável por mensagem.",
        )
        for name in ("roadmap.md", "alpha_readiness.md", "implementation_matrix.md"):
            text = (PRODUCT_DOCS / name).read_text(encoding="utf-8")
            for restriction in restrictions:
                with self.subTest(document=name, restriction=restriction):
                    self.assertIn(restriction, text)

    def test_readme_preserves_public_caveats(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        scope = text.split("## Current scope", 1)[1].split("## Requirements", 1)[0]
        for statement in (
            "Effective authorization currently covers `adapter-dry-run` and one real "
            "local non-dry-run path: `local-status-read` for `local_status.status`.",
            "Browser, n8n, voice, broad MCP execution and social/career automation "
            "are not ready-to-use features.",
            "It is not general agent messaging authority or durable per-message approval.",
            "New governed sends require explicit approval of content and destination plus the roadmap gates.",
            "PR100 adds a read-only `alpha-readiness` go/no-go check for a public technical alpha candidate; "
            "publication remains a separate explicit human decision and the product is not declared complete.",
        ):
            self.assertIn(statement, scope)
        for name in ("index.md", "roadmap.md", "implementation_matrix.md", "alpha_readiness.md"):
            self.assertIn(f"](docs/product/{name})", scope)

    def test_index_classifies_documents_and_defines_precedence(self) -> None:
        text = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        for classification in (
            "**normativo** — [Roadmap]",
            "**matriz de estado, descritivo** — [Implementation matrix]",
            "**prontidão alpha, critérios normativos** — [Alpha readiness]",
            "**descritivo, consolidação de revisão externa** — [Consolidação das revisões]",
            "**revisão externa / histórico** — [Revisão Astra]",
            "**spec de PR / histórico**",
        ):
            self.assertIn(classification, text)
        self.assertIn(
            "Para sequência prevalece o roadmap; para estado atual, a matriz; "
            "para publicação, os critérios de readiness.", text,
        )
        self.assertIn(
            "Revisões externas e specs históricas não sobrepõem os documentos normativos atuais", text,
        )

    def test_matrix_evidence_links_exist(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue((PRODUCT_DOCS / link).is_file(), link)


    def test_public_quickstart_exists_and_is_source_first(self) -> None:
        quickstart = ROOT / "docs" / "quickstart.md"
        self.assertTrue(quickstart.is_file())
        text = quickstart.read_text(encoding="utf-8")
        for statement in (
            "source checkout validation",
            "editable local wrapper installation without `pip install`",
            "scripts/install-local.sh",
            "export PATH=\"$HOME/.local/bin:$PATH\"",
            "PYTHON=python3 make check",
            "lai-gateway-stack-check",
            "--harness-repo /path/to/workspace/lai-harness-checkout",
            "lai-gateway doctor",
            "lai-gateway readiness",
            "lai-gateway dev --bind 127.0.0.1 --port 8787 --no-open",
            "http://127.0.0.1:8787/",
            "lai-gateway stack-start --check-only",
        ):
            self.assertIn(statement, text)

    def test_public_quickstart_does_not_overclaim_alpha_capabilities(self) -> None:
        text = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
        for statement in (
            "It does not cover a one-click installer, PyPI release, hosted service, cloud",
            "authenticated browser sessions, real n8n activation, broad MCP",
            "external message/publication automation",
            "prove general adapter authorization",
            "does not enable browser, n8n, voice, MCP",
            "LAI is a finished product.",
        ):
            self.assertIn(statement, text)
        self.assertNotIn("one-click installer is ready", text)
        self.assertNotIn("browser automation is ready", text)
        self.assertNotIn("n8n workflows are ready", text)

    def test_pr91_is_linked_from_canonical_public_docs(self) -> None:
        self.assertTrue((PRODUCT_DOCS / "pr_91_public_quickstart.md").is_file())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        self.assertIn("](docs/quickstart.md)", readme)
        self.assertIn("[Quickstart](../quickstart.md)", index)
        self.assertIn("`docs/quickstart.md`", roadmap)
        self.assertIn("Após o PR91, `docs/quickstart.md`", alpha)
        self.assertIn("não transforma o alpha em produto completo", alpha)
    def test_pr92_release_checklist_identifies_source_artifact(self) -> None:
        release_checklist = ROOT / "docs" / "release_checklist.md"
        self.assertTrue(release_checklist.is_file())
        text = release_checklist.read_text(encoding="utf-8")
        with open(ROOT / "pyproject.toml", "rb") as handle:
            project_version = tomllib.load(handle)["project"]["version"]
        for statement in (
            "source-first",
            "versão declarada em `lai_gateway.__version__` e `pyproject.toml`",
            "commit exato integrado em `main` por PR com CI verde",
            f"python3 -m lai_gateway release-check --target {project_version} --json",
            f"TARGET_GATEWAY={project_version}",
            "PYTHON=python3 make check",
            "make milestone-gate",
            "Não há promessa de PyPI, binário, instalador one-click, hosted service ou cloud",
            "não publica tags, releases, pacotes, mensagens ou artefatos externos",
        ):
            self.assertIn(statement, text)

    def test_pr92_workbench_visual_guide_is_sanitized_and_restricted(self) -> None:
        guide = ROOT / "docs" / "workbench_visual_guide.md"
        self.assertTrue(guide.is_file())
        text = guide.read_text(encoding="utf-8")
        for statement in (
            "Guia visual mínimo e sanitizado",
            "conversa normal `@lai` sem criar run dev implícito",
            "painel Governance",
            "fluxo seguro `local_status`",
            "Evidência visual sanitizada",
            "sem shell",
            "sem filesystem write",
            "sem rede externa",
            "sem credenciais",
            "sem MCP tool call",
            "sem envio de mensagem",
            "sem prova de autorização geral",
            "Este guia não implementa UI nova",
        ):
            self.assertIn(statement, text)
        for blocked in ("browser agent", "n8n real", "voz operacional", "MCP tool execution amplo", "publicação externa"):
            self.assertIn(blocked, text)
        self.assertNotIn("browser automation is ready", text)
        self.assertNotIn("n8n workflows are ready", text)

    def test_pr92_docs_are_linked_from_canonical_public_docs(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        self.assertTrue((PRODUCT_DOCS / "pr_92_release_workbench_guide.md").is_file())
        self.assertIn("](docs/release_checklist.md)", readme)
        self.assertIn("](docs/workbench_visual_guide.md)", readme)
        self.assertIn("[Release checklist](../release_checklist.md)", index)
        self.assertIn("[Workbench visual guide](../workbench_visual_guide.md)", index)
        self.assertIn("`docs/release_checklist.md`", roadmap)
        self.assertIn("`docs/workbench_visual_guide.md`", roadmap)
        self.assertIn("Após o PR92, `docs/release_checklist.md`", alpha)
        self.assertIn("não publicam release, não fazem bump/tag e não habilitam capacidades externas", alpha)


if __name__ == "__main__":
    unittest.main()
