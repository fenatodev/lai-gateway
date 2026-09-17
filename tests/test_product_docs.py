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
            "pr_106_public_browser_readonly.md",
            "pr_107_mcp_minimal_governed.md",
            "pr_108_n8n_minimal_governed.md",
            "pr_109_permission_ux.md",
            "pr_110_external_expansion_gate.md",
            "post_pr110_operating_plan.md",
            "project_workspace_contract.md",
            "objective_state.md",
            "action_proposal.md",
            "approval_inbox.md",
            "pr_111_operating_objective_plan.md",
            "pr_112_project_workspace_contract.md",
            "pr_113_objective_state.md",
            "pr_114_action_proposal.md",
            "pr_115_approval_inbox.md",
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
        self.assertIn("browser | experimental", text)
        self.assertIn("n8n | experimental", text)
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
            "Continuam bloqueados na expansão governada: browser autenticado, n8n activation/execução real de workflow, "
            "MCP tool execution amplo, publicação, envio de mensagens, candidaturas, formulários, "
            "automações externas e uso de credenciais.", external,
        )
        for capability in ("browser autenticado", "n8n activation/execução real de workflow", "MCP tool execution amplo", "publicação", "envio de mensagens", "candidaturas", "formulários", "automações externas", "uso de credenciais"):
            self.assertIn(capability, external)

    def test_matrix_does_not_promote_contracts_or_dry_run_to_execution(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        rows = {}
        for line in text.splitlines():
            if line.startswith("| ") and not line.startswith("| ---"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0]] = cells[1:]
        for area in ("voice", "MCP execution", "social/career", "document/media"):
            self.assertEqual(rows[area][0], "contract", area)
        self.assertEqual(rows["n8n"][0], "experimental")
        self.assertIn("sem instalar/iniciar n8n", rows["n8n"][4])
        self.assertIn("activation", rows["n8n"][4])
        self.assertIn("execução real de workflow", rows["n8n"][4])
        self.assertEqual(rows["browser"][0], "experimental")
        self.assertIn("public-browser-read/v1", rows["browser"][4])
        self.assertIn("sem browser autenticado", rows["browser"][4])
        self.assertEqual(rows["identidade usuário/cliente/agente/serviço"][0], "experimental")
        self.assertEqual(rows["identidade usuário/cliente/agente/serviço"][1], "binding local testável")
        self.assertEqual(rows["effective authorization"][0], "experimental")
        self.assertEqual(rows["permission_ux"][0], "experimental")
        self.assertIn("permission-ux/v1", rows["permission_ux"][4])
        self.assertIn("sem emitir grant", rows["permission_ux"][4])
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
        self.assertIn("`local-status-read`/`local_status.status`", alpha)
        self.assertIn("`mcp-local-safe-tool`/`mcp.local_echo_digest`", alpha)
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


    def test_pr106_public_browser_readonly_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_106_public_browser_readonly.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        module = (ROOT / "lai_gateway" / "public_browser.py").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, html, js, module])
        for marker in (
            "public-browser-read/v1",
            "Browser público",
            "GET público único",
            "Sem browser autenticado",
            "Sem cookies",
            "Sem JavaScript automation",
            "Sem formulário",
            "Sem download de arquivo",
            "Conteúdo recuperado da web é não confiável",
            "não concede autoridade",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR106](pr_106_public_browser_readonly.md)", index)
        self.assertIn("/v1/gateway/public-browser", js)
        self.assertIn("public-browser-output", html)
        self.assertNotIn("browser automation is ready", combined)


    def test_pr107_mcp_minimal_governed_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_107_mcp_minimal_governed.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, html, js])
        for marker in (
            "mcp-local-tool/v1",
            "mcp.local_echo_digest",
            "mcp-local-safe-tool",
            "grant single-use",
            "bloqueio de replay",
            "identidade verificada",
            "Sem `mcp.call_tool` amplo",
            "Sem broker MCP externo",
            "Sem credenciais",
            "Sem shell",
            "Sem rede",
            "não concede autorização",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR107](pr_107_mcp_minimal_governed.md)", index)
        self.assertIn("mcp_local | experimental", matrix)
        self.assertIn("mcp_local", matrix)
        self.assertIn("/v1/gateway/mcp-local-tool", js)
        self.assertIn("issue-mcp-local-tool", html)
        self.assertIn("run-mcp-local-tool", html)

    def test_pr108_n8n_minimal_governed_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_108_n8n_minimal_governed.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, html, js])
        for marker in (
            "n8n-local-plan/v1",
            "n8n.local_plan_digest",
            "n8n-local-plan",
            "workflow_sha256",
            "grant single-use",
            "sem execução real de workflow",
            "sem instalar/iniciar n8n",
            "sem credenciais",
            "sem rede",
            "sem shell",
            "sem webhook",
            "não concede autorização",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR108](pr_108_n8n_minimal_governed.md)", index)
        self.assertIn("n8n | experimental", matrix)
        self.assertIn("/v1/gateway/n8n-local-plan", js)
        self.assertIn("issue-n8n-local-plan", html)
        self.assertIn("inspect-n8n-local-plan", html)
        self.assertNotIn("n8n workflows are ready", combined)

    def test_pr109_permission_ux_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_109_permission_ux.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, alpha, html, js])
        for marker in (
            "permission-ux/v1",
            "intenção",
            "decisão",
            "autorização efetiva",
            "grant",
            "execução",
            "não emite grant",
            "não consome grant",
            "não despacha adapter",
            "não concede autoridade",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR109](pr_109_permission_ux.md)", index)
        self.assertIn("permission_ux | experimental", matrix)
        self.assertIn("/v1/gateway/permission-ux", js)
        self.assertIn("refresh-permission-ux", html)
        self.assertNotIn("permission UX grants authorization", combined)

    def test_pr110_external_expansion_gate_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_110_external_expansion_gate.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        post = (PRODUCT_DOCS / "post_pr100_roadmap.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        module = (ROOT / "lai_gateway" / "external_expansion.py").read_text(encoding="utf-8")
        combined = "\n".join([spec, index, post, matrix, alpha, readme, html, js, module])
        for marker in (
            "external-expansion-gate/v1",
            "PR110",
            "go/no-go",
            "no-go read-only",
            "não habilita capacidades externas",
            "browser autenticado",
            "n8n real",
            "MCP amplo",
            "credenciais",
            "publicação",
            "não emite grant",
            "não consome grant",
            "não despacha adapter",
        ):
            self.assertIn(marker, combined)
        self.assertIn("[PR110](pr_110_external_expansion_gate.md)", index)
        self.assertIn("external expansion gate | experimental", matrix)
        self.assertIn("/v1/gateway/external-expansion-gate", js)
        self.assertIn("refresh-external-expansion-gate", html)
        self.assertNotIn("external capabilities are enabled", combined)
        self.assertNotIn("authenticated browser is ready", combined)
        self.assertNotIn("n8n real workflows are ready", combined)

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
            "Browser autenticado, n8n activation/execução real de workflow, voz, execução ampla/externa de tools MCP, social e automações externas "
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
            "Authenticated browser sessions, n8n activation/real workflow execution, voice, broad/external MCP execution and social/career automation "
            "are not ready-to-use features.",
            "PR109 adds a read-only permission UX that separates intent, decision, effective authorization, grant and execution; "
            "it does not issue grants, consume grants or dispatch adapters.",
            "PR110 adds `external-expansion-gate/v1`, a read-only external expansion gate; "
            "it keeps external effects in no-go and does not enable browser authenticated sessions, n8n real workflows, "
            "broad MCP, credentials, publication, messaging, grants, dispatch or tool execution.",
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

    def test_pr111_operating_objective_plan_is_canonical_and_limited(self) -> None:
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_111_operating_objective_plan.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("sistema operacional pessoal de IA local", plan)
        self.assertIn("alpha operacional local", plan)
        self.assertIn("PR110 permanece como no-go", plan)
        rows = re.findall(r"^\| PR(\d+) \| (.+)$", plan, re.MULTILINE)
        self.assertEqual([int(number) for number, _ in rows], list(range(111, 121)))
        self.assertLess(plan.index("| PR112 |"), plan.index("| PR119 |"))
        self.assertLess(plan.index("| PR118 |"), plan.index("| PR120 |"))
        for blocked in (
            "Browser autenticado",
            "n8n activation ou execução real de workflow",
            "MCP amplo ou execução externa de tools",
            "Uso de credenciais por agente",
            "Envio governado de mensagens",
            "PDF/OCR/Office/mídia ampla",
        ):
            self.assertIn(blocked, plan)
        for statement in (
            "sem mudança funcional",
            "não altera executor, adapter, grant, policy runtime",
            "não libera capacidades externas",
            "não deve ser lido como evidência de capacidade operacional nova",
        ):
            self.assertIn(statement, spec)
        self.assertIn("[Plano operacional pós-PR110](post_pr110_operating_plan.md)", index)
        self.assertIn("[PR111](pr_111_operating_objective_plan.md)", index)
        self.assertIn("operating objective plan | contract", matrix)
        self.assertIn("não cria executor, grant, adapter", matrix)
        self.assertIn("Após o PR111", alpha)
        self.assertIn("does not create an executor, grant, adapter", readme)

    def test_pr112_project_workspace_contract_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "project_workspace_contract.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_112_project_workspace_contract.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for statement in (
            "root_path explícito",
            "allowed_relative_roots",
            "excluded_relative_roots",
            "data_touched",
            "capabilities_granted",
            "A raiz do workspace deve ser escolhida pelo operador",
            "HOME scan",
            "ingestão implícita",
            "Conteúdo encontrado no workspace continua dado não confiável",
        ):
            self.assertIn(statement, contract)
        for blocked in (
            "Não cria scanner de arquivos",
            "Não cria endpoint, CLI ou UI nova",
            "Não altera executor, adapter, grant ou policy runtime",
            "Não faz HOME scan",
            "Não faz ingestão implícita",
            "Não libera capacidades externas",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("[Project workspace contract](project_workspace_contract.md)", index)
        self.assertIn("[PR112](pr_112_project_workspace_contract.md)", index)
        self.assertIn("project workspace contract | contract", matrix)
        self.assertIn("sem HOME scan, ingestão implícita, executor, grant, adapter", matrix)
        self.assertIn("Após o PR112", alpha)
        self.assertIn("does not scan HOME, ingest files implicitly", readme)


    def test_pr113_objective_state_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "objective_state.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_113_objective_state.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "objective-state/v1",
            "workspace_root explícita",
            ".lai/objective-state.json",
            "data_touched",
            "Conteúdo lido do estado continua não confiável",
        ):
            self.assertIn(statement, contract)
        for blocked in (
            "Não cria scanner recursivo",
            "Não faz HOME scan",
            "Não faz ingestão implícita",
            "Não escreve arquivo de estado",
            "Não emite grants",
            "Não despacha adapters",
            "Não chama Harness",
            "Não executa tools",
            "Não libera capacidades externas",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("[Objective state](objective_state.md)", index)
        self.assertIn("[PR113](pr_113_objective_state.md)", index)
        self.assertIn("objective_state | experimental", matrix)
        self.assertIn("`objective-state/v1`", matrix)
        self.assertIn("Após o PR113", alpha)
        self.assertIn("does not write state, scan HOME", readme)
        self.assertIn("objective-state", main_py)
        self.assertIn("/v1/gateway/objective-state", server_py)
        self.assertIn("refresh-objective-state", app)
        self.assertIn("objective-output", html)


    def test_pr114_action_proposal_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "action_proposal.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_114_action_proposal.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "action-proposal/v1",
            "domínio, canal, autonomia e capacidade",
            "target",
            "data",
            "effect",
            "risk",
            "proposal_only: true",
            "effective_authorization: false",
            "Conteúdo de objetivo/tarefa/checkpoint continua não confiável",
        ):
            self.assertIn(statement, contract)
        for blocked in (
            "Não cria approval inbox",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não executa tools",
            "Não chama Harness",
            "Não escreve estado local",
            "Não faz HOME scan",
            "Não faz ingestão implícita",
            "Não libera capacidades externas",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR114 | Proposta unificada | `action-proposal/v1`", plan)
        self.assertIn("[Action proposal](action_proposal.md)", index)
        self.assertIn("[PR114](pr_114_action_proposal.md)", index)
        self.assertIn("action_proposal | experimental", matrix)
        self.assertIn("sem autorização efetiva, grants, adapter dispatch", matrix)
        self.assertIn("Após o PR114", alpha)
        self.assertIn("action-proposal/v1", readme)
        self.assertIn("action-proposal", main_py)
        self.assertIn("/v1/gateway/action-proposal", server_py)
        self.assertIn("refresh-action-proposal", app)
        self.assertIn("action-proposal-output", html)



    def test_pr115_approval_inbox_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "approval_inbox.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_115_approval_inbox.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "approval-inbox/v1",
            ".lai/approval-inbox.jsonl",
            "registros pendentes",
            "domínio, canal, autonomia, capacidade",
            "não concedem autoridade",
        ):
            self.assertIn(statement, contract)
        for blocked in (
            "Não habilita browser autenticado",
            "Não ativa n8n real",
            "Não chama MCP amplo",
            "Não usa credenciais",
            "Não envia mensagem",
            "Não publica",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não chama Harness",
            "Não executa tool",
            "Não realiza efeito externo",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR115 | Caixa de aprovação | `approval-inbox/v1`", plan)
        self.assertIn("[Approval inbox](approval_inbox.md)", index)
        self.assertIn("[PR115](pr_115_approval_inbox.md)", index)
        self.assertIn("approval_inbox | experimental", matrix)
        self.assertIn("sem autorização efetiva, grants, credenciais", matrix)
        self.assertIn("Após o PR115", alpha)
        self.assertIn("approval-inbox/v1", readme)
        self.assertIn("approval-inbox", main_py)
        self.assertIn("/v1/gateway/approval-inbox", server_py)
        self.assertIn("refresh-approval-inbox", app)
        self.assertIn("approval-inbox-output", html)


    def test_pr116_dev_loop_fixture_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_116_dev_loop_fixture.md").read_text(encoding="utf-8")
        contract = (PRODUCT_DOCS / "dev_loop_fixture.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "dev-loop-fixture/v1",
            "Observe/Work/Review/Apply",
            "fixture local",
            "source checkout",
        ):
            self.assertIn(statement, spec + contract)
        for blocked in (
            "Não habilita browser autenticado",
            "Não ativa n8n real",
            "Não chama MCP amplo",
            "Não usa credenciais",
            "Não envia mensagem",
            "Não publica",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não chama Harness",
            "Não executa tools",
            "Não escreve source checkout",
            "Não faz merge automático",
            "Não faz HOME scan",
            "Não faz ingestão implícita",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR116 | Loop dev local controlado | `dev-loop-fixture/v1`", plan)
        self.assertIn("[Dev loop fixture](dev_loop_fixture.md)", index)
        self.assertIn("[PR116](pr_116_dev_loop_fixture.md)", index)
        self.assertIn("dev_loop_fixture | experimental", matrix)
        self.assertIn("sem autorização efetiva, grants, credenciais", matrix)
        self.assertIn("Após o PR116", alpha)
        self.assertIn("dev-loop-fixture/v1", readme)
        self.assertIn("dev-loop-fixture", main_py)
        self.assertIn("/v1/gateway/dev-loop-fixture", server_py)
        self.assertIn("refresh-dev-loop-fixture", app)
        self.assertIn("dev-loop-fixture-output", html)

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

    def test_pr117_context_pack_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_117_context_pack.md").read_text(encoding="utf-8")
        contract = (PRODUCT_DOCS / "context_pack.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "context-pack/v1",
            "contexto local explícito",
            "documentos selecionados",
            "conteúdo não confiável",
        ):
            self.assertIn(statement, spec + contract)
        for blocked in (
            "Não habilita browser autenticado",
            "Não ativa n8n real",
            "Não chama MCP amplo",
            "Não usa credenciais",
            "Não envia mensagem",
            "Não publica",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não chama Harness",
            "Não executa tools",
            "Não escreve arquivos",
            "Não faz HOME scan",
            "Não faz varredura recursiva ampla",
            "Não faz ingestão implícita",
            "Não exige embeddings",
            "Não gera embeddings",
            "Não realiza efeito externo",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR117 | Context pack local | `context-pack/v1`", plan)
        self.assertIn("[Context pack](context_pack.md)", index)
        self.assertIn("[PR117](pr_117_context_pack.md)", index)
        self.assertIn("context_pack | experimental", matrix)
        self.assertIn("sem autorização efetiva, grants, credenciais, embeddings obrigatórios", matrix)
        self.assertIn("Após o PR117", alpha)
        self.assertIn("context-pack/v1", readme)
        self.assertIn("context-pack", main_py)
        self.assertIn("/v1/gateway/context-pack", server_py + app)
        self.assertIn('id="context-pack-output"', html)
        self.assertIn('data-action="refresh-context-pack"', html)

    def test_pr118_model_runtime_profile_is_canonical_and_limited(self) -> None:
        spec = (PRODUCT_DOCS / "pr_118_model_runtime_profile.md").read_text(encoding="utf-8")
        contract = (PRODUCT_DOCS / "model_runtime_profile.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "model-runtime-profile/v1",
            "perfil UX read-only",
            "runtime local",
            "fallback",
        ):
            self.assertIn(statement, spec + contract)
        for blocked in (
            "Não baixa modelo",
            "Não inicia runtime",
            "Não inicia servidor",
            "Não chama endpoint público",
            "Não roda probe local automaticamente",
            "Não usa cloud fallback",
            "Não imprime token",
            "Não escreve arquivo",
            "Não executa tool",
            "Não chama Harness",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não habilita browser autenticado",
            "Não ativa n8n real",
            "Não chama MCP amplo",
            "Não envia mensagem",
            "Não publica",
            "Não realiza efeito externo",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR118 | Modelo local operacional UX | `model-runtime-profile/v1`", plan)
        self.assertIn("[Model runtime profile](model_runtime_profile.md)", index)
        self.assertIn("[PR118](pr_118_model_runtime_profile.md)", index)
        self.assertIn("model_runtime_profile | experimental", matrix)
        self.assertIn("sem baixar modelo, iniciar runtime", matrix)
        self.assertIn("Após o PR118", alpha)
        self.assertIn("model-runtime-profile/v1", readme)
        self.assertIn("model-runtime-profile", main_py)
        self.assertIn("/v1/gateway/model-runtime-profile", server_py + app)
        self.assertIn('id="model-runtime-profile-output"', html)
        self.assertIn('data-action="refresh-model-runtime-profile"', html)


    def test_pr119_public_browser_v2_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "public_browser_inspector.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_119_public_browser_v2.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "public-browser-inspector/v1",
            "source inspector público restrito",
            "domínio, canal, autonomia, capacidade",
            "links públicos como strings inertes",
        ):
            self.assertIn(statement, spec + contract)
        for blocked in (
            "Não habilita browser autenticado",
            "Não usa cookies",
            "Não executa JavaScript",
            "Não submete formulários",
            "Não faz download",
            "Não segue links",
            "Não usa credenciais",
            "Não envia mensagem",
            "Não publica",
            "Não ativa n8n real",
            "Não chama MCP amplo",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não chama Harness",
            "Não executa tools",
            "Não realiza efeito externo",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR119 | Browser público v2 | `public-browser-inspector/v1`", plan)
        self.assertIn("[Public browser inspector](public_browser_inspector.md)", index)
        self.assertIn("[PR119](pr_119_public_browser_v2.md)", index)
        self.assertIn("public-browser-inspector/v1", matrix)
        self.assertIn("sem browser autenticado, cookies, JS automation", matrix)
        self.assertIn("Após o PR119", alpha)
        self.assertIn("public-browser-inspector/v1", readme)
        self.assertIn("inspect", main_py)
        self.assertIn("/v1/gateway/public-browser", server_py + app)
        self.assertIn("inspect-public-browser", app)
        self.assertIn('data-action="inspect-public-browser"', html)

    def test_pr120_external_capability_gate_is_canonical_and_limited(self) -> None:
        contract = (PRODUCT_DOCS / "external_capability_gate.md").read_text(encoding="utf-8")
        spec = (PRODUCT_DOCS / "pr_120_external_capability_gate.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        plan = (PRODUCT_DOCS / "post_pr110_operating_plan.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        main_py = (ROOT / "lai_gateway" / "__main__.py").read_text(encoding="utf-8")
        server_py = (ROOT / "lai_gateway" / "server.py").read_text(encoding="utf-8")
        app = (ROOT / "lai_gateway" / "static" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "lai_gateway" / "static" / "index.html").read_text(encoding="utf-8")

        for statement in (
            "external-capability-gate/v1",
            "browser.public_source_inspection",
            "Domínio: governança de capacidade externa",
            "Canal: CLI, API protegida do Gateway e Workbench",
            "Autonomia: avaliação read-only",
            "Capacidade: `external_capability.go_no_go_candidate`",
        ):
            self.assertIn(statement, spec + contract)
        for blocked in (
            "Não habilita browser autenticado",
            "Não usa cookies",
            "Não executa JavaScript",
            "Não submete formulários",
            "Não faz download",
            "Não segue links",
            "Não usa credenciais",
            "Não envia mensagem",
            "Não publica",
            "Não ativa n8n real",
            "Não executa workflow n8n",
            "Não chama MCP amplo",
            "Não cria autorização efetiva",
            "Não emite grant",
            "Não consome grant",
            "Não despacha adapter",
            "Não chama Harness",
            "Não executa tools",
            "Não realiza efeito externo",
        ):
            self.assertIn(blocked, spec)
        self.assertIn("| PR120 | Gate de primeira capacidade externa | `external-capability-gate/v1`", plan)
        self.assertIn("[External capability gate](external_capability_gate.md)", index)
        self.assertIn("[PR120](pr_120_external_capability_gate.md)", index)
        self.assertIn("external_capability_gate | experimental", matrix)
        self.assertIn("sem apresentar o gate como browser autenticado", spec)
        self.assertIn("Após o PR120", alpha)
        self.assertIn("external-capability-gate/v1", readme)
        self.assertIn("external-capability-gate", main_py)
        self.assertIn("/v1/gateway/external-capability-gate", server_py + app)
        self.assertIn('id="external-capability-output"', html)
        self.assertIn('data-action="refresh-external-capability-gate"', html)

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



class LocalOperatorProductDocsTest(unittest.TestCase):
    def _read(self, relative_path):
        root = Path(__file__).resolve().parents[1]
        return (root / relative_path).read_text(encoding="utf-8")

    def test_pr121_local_operator_spec_is_documented_and_non_executing(self):
        local_operator = self._read("docs/product/local_operator.md")
        pr_note = self._read("docs/product/pr_121_local_operator_spec.md")
        combined = (local_operator + "\n" + pr_note).lower()

        for marker in (
            "local-operator-spec/v1",
            "documentation only",
            "does not create an executor",
            "does not execute commands",
            "does not issue grants",
            "does not consume grants",
            "does not change permissions",
            "gateway",
            "harness",
            "aider",
            "ollama",
            "never equals authorization",
        ):
            self.assertIn(marker, combined)

        for forbidden_marker in (
            "sudo",
            "credential",
            "authenticated browser",
            "message sending",
            "publication",
            "merge to `main`",
            "broad `$home` access",
        ):
            self.assertIn(forbidden_marker, combined)

    def test_pr121_local_operator_is_indexed_as_specified_not_implemented(self):
        docs = {
            "index": self._read("docs/product/index.md"),
            "matrix": self._read("docs/product/implementation_matrix.md"),
            "plan": self._read("docs/product/post_pr110_operating_plan.md"),
            "alpha": self._read("docs/product/alpha_readiness.md"),
        }

        for name, content in docs.items():
            with self.subTest(name=name):
                self.assertIn("local-operator-spec/v1", content)

        matrix = docs["matrix"].lower()
        self.assertIn("specified", matrix)
        self.assertIn("not implemented", matrix)
        self.assertIn("sem executor", matrix)
        self.assertIn("sem executor, shell, grants", matrix)

        alpha = docs["alpha"]
        self.assertIn("Após o PR121", alpha)
        self.assertIn("não cria executor", alpha)
        self.assertIn("não adiciona shell", alpha)
        self.assertIn("não emite grant", alpha)
        self.assertIn("não consome grant", alpha)
        self.assertIn("não altera permissões", alpha)


class LocalTaskFormatProductDocsTest(unittest.TestCase):
    def _read(self, relative_path):
        root = Path(__file__).resolve().parents[1]
        return (root / relative_path).read_text(encoding="utf-8")

    def test_pr122_local_task_format_is_documented_and_non_executing(self):
        spec = self._read("docs/product/local_task_format.md")
        pr_note = self._read("docs/product/pr_122_local_task_format.md")
        combined = (spec + "\n" + pr_note).lower()

        for marker in (
            "local-task-format/v1",
            "local-task/v1",
            "local-task-outbox/v1",
            ".lai-ai/tasks",
            ".lai-ai/outbox",
            ".lai-ai/logs",
            "documentation only",
            "does not create an executor",
            "does not execute commands",
            "does not add a shell",
            "does not issue grants",
            "does not consume grants",
            "does not change permissions",
            "never equals authorization",
        ):
            self.assertIn(marker, combined)

        for forbidden_marker in (
            "sudo",
            "credential",
            "authenticated browser",
            "message sending",
            "publication",
            "merge to `main`",
            "broad `$home` access",
            "adapter dispatch",
        ):
            self.assertIn(forbidden_marker, combined)

    def test_pr122_local_task_format_is_indexed_as_planned_not_implemented(self):
        docs = {
            "index": self._read("docs/product/index.md"),
            "matrix": self._read("docs/product/implementation_matrix.md"),
            "plan": self._read("docs/product/post_pr110_operating_plan.md"),
            "alpha": self._read("docs/product/alpha_readiness.md"),
        }

        for name, content in docs.items():
            with self.subTest(name=name):
                self.assertIn("local-task-format/v1", content)

        matrix = docs["matrix"].lower()
        self.assertIn("| local_task_format | planned |", matrix)
        self.assertIn("specified, not implemented", matrix)
        self.assertIn("sem criar diretórios", matrix)
        self.assertIn("sem criar diretórios, executor, shell", matrix)

        alpha = docs["alpha"]
        self.assertIn("Após o PR122", alpha)
        self.assertIn("não cria `.lai-ai/tasks`", alpha)
        self.assertIn("não cria executor", alpha)
        self.assertIn("não adiciona shell", alpha)
        self.assertIn("não emite grant", alpha)
        self.assertIn("não consome grant", alpha)
        self.assertIn("não altera permissões", alpha)



class LocalTaskDryRunProductDocsTest(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_pr123_local_task_dry_run_is_documented_as_read_only(self):
        spec = self._read("docs/product/local_task_dry_run.md")
        pr_note = self._read("docs/product/pr_123_local_task_dry_run.md")
        combined = f"{spec}\n{pr_note}".lower()

        required_markers = [
            "local-task-dry-run/v1",
            "local-task/v1",
            "local-task-outbox/v1",
            "read-only",
            "dry-run",
            "never authorization",
            "does not execute commands",
            "does not call harness",
            "does not call tools",
            "does not dispatch adapters",
            "does not issue grants",
            "does not consume grants",
            "does not use credentials",
            "does not send messages",
            "does not publish",
            "does not merge `main`",
            "external side effects",
        ]

        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_pr123_local_task_dry_run_is_indexed_as_implemented(self):
        index = self._read("docs/product/index.md")
        matrix = self._read("docs/product/implementation_matrix.md")
        plan = self._read("docs/product/post_pr110_operating_plan.md")
        alpha = self._read("docs/product/alpha_readiness.md")

        self.assertIn("local_task_dry_run.md", index)
        self.assertIn("`local-task-dry-run/v1`", index)

        self.assertIn("| local_task_dry_run | implemented |", matrix)
        self.assertIn("[spec](local_task_dry_run.md)", matrix)
        self.assertIn("[PR123](pr_123_local_task_dry_run.md)", matrix)
        self.assertIn("sem executor", matrix)
        self.assertIn("sem executor, shell", matrix)

        self.assertIn("PR123 implementa `local-task-dry-run/v1`", plan)
        self.assertIn("sem executor, shell, grants", plan)

        self.assertIn("Após o PR123", alpha)
        self.assertIn("não executa comandos", alpha)
        self.assertIn("não chama Harness", alpha)
        self.assertIn("não chama tools", alpha)
        self.assertIn("não despacha adapters", alpha)
        self.assertIn("não emite grant", alpha)
        self.assertIn("não consome grant", alpha)
        self.assertIn("não produz efeito externo", alpha)

class LocalTaskFilePackProductDocsTest(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_pr124_local_task_file_pack_is_documented_as_bounded_file_pack(self):
        spec = self._read("docs/product/local_task_file_pack.md")
        pr_note = self._read("docs/product/pr_124_local_task_file_pack.md")
        combined = f"{spec}\n{pr_note}".lower()

        required_markers = [
            "local-task-file-pack/v1",
            "local-task/v1",
            "local-task-outbox/v1",
            ".lai-ai/tasks",
            ".lai-ai/outbox",
            "--write",
            "default mode is plan-only",
            "repository-relative",
            "must not contain parent traversal",
            "never authorization",
            "command execution",
            "harness calls",
            "tool calls",
            "adapter dispatch",
            "grant issuance",
            "grant consumption",
            "credential access",
            "external side effects",
        ]

        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_pr124_local_task_file_pack_is_indexed_as_implemented(self):
        index = self._read("docs/product/index.md")
        matrix = self._read("docs/product/implementation_matrix.md")
        plan = self._read("docs/product/post_pr110_operating_plan.md")
        alpha = self._read("docs/product/alpha_readiness.md")

        self.assertIn("local_task_file_pack.md", index)
        self.assertIn("`local-task-file-pack/v1`", index)

        self.assertIn("| local_task_file_pack | implemented |", matrix)
        self.assertIn("[spec](local_task_file_pack.md)", matrix)
        self.assertIn("[PR124](pr_124_local_task_file_pack.md)", matrix)
        self.assertIn("`.lai-ai/tasks`", matrix)
        self.assertIn("`.lai-ai/outbox`", matrix)
        self.assertIn("sem executor, shell", matrix)

        self.assertIn("PR124 implementa `local-task-file-pack/v1`", plan)
        self.assertIn("sem executor, shell, Harness", plan)

        self.assertIn("Após o PR124", alpha)
        self.assertIn("não executa comandos", alpha)
        self.assertIn("não chama Harness", alpha)
        self.assertIn("não chama tools", alpha)
        self.assertIn("não despacha adapters", alpha)
        self.assertIn("não emite grant", alpha)
        self.assertIn("não consome grant", alpha)
        self.assertIn("não produz efeito externo", alpha)

class LocalTaskReviewGateProductDocsTest(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_pr125_local_task_review_gate_is_documented_as_read_only_gate(self):
        spec = self._read("docs/product/local_task_review_gate.md")
        pr_note = self._read("docs/product/pr_125_local_task_review_gate.md")
        combined = f"{spec}\n{pr_note}".lower()

        required_markers = [
            "local-task-review-gate/v1",
            "local-task/v1",
            "local-task-outbox/v1",
            "ready",
            "blocked",
            "invalid",
            "read-only",
            "not authorization",
            "does not execute",
            "run shell commands",
            "call harness",
            "call tools",
            "dispatch adapters",
            "issue grants",
            "consume grants",
            "use credentials",
            "external side effects",
        ]

        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_pr125_local_task_review_gate_is_indexed_as_implemented(self):
        index = self._read("docs/product/index.md")
        matrix = self._read("docs/product/implementation_matrix.md")
        plan = self._read("docs/product/post_pr110_operating_plan.md")
        alpha = self._read("docs/product/alpha_readiness.md")

        self.assertIn("local_task_review_gate.md", index)
        self.assertIn("`local-task-review-gate/v1`", index)

        self.assertIn("| local_task_review_gate | implemented |", matrix)
        self.assertIn("[spec](local_task_review_gate.md)", matrix)
        self.assertIn("[PR125](pr_125_local_task_review_gate.md)", matrix)
        self.assertIn("ready/blocked/invalid", matrix)
        self.assertIn("sem executor, shell", matrix)

        self.assertIn("PR125 implementa `local-task-review-gate/v1`", plan)
        self.assertIn("ready/blocked/invalid", plan)

        self.assertIn("Após o PR125", alpha)
        self.assertIn("não executa comandos", alpha)
        self.assertIn("não modifica arquivos de tarefa", alpha)
        self.assertIn("não chama Harness", alpha)
        self.assertIn("não chama tools", alpha)
        self.assertIn("não despacha adapters", alpha)
        self.assertIn("não emite grant", alpha)
        self.assertIn("não consome grant", alpha)
        self.assertIn("não produz efeito externo", alpha)

if __name__ == "__main__":
    unittest.main()

class LocalTaskApprovalGateProductDocsTest(unittest.TestCase):
    def test_pr126_local_task_approval_gate_is_documented_as_advisory_read_only_gate(self) -> None:
        spec = (PRODUCT_DOCS / "local_task_approval_gate.md").read_text(encoding="utf-8")
        pr_spec = (PRODUCT_DOCS / "pr_126_local_task_approval_gate.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")

        for statement in (
            "local-task-approval-gate/v1",
            "ready_without_approval",
            "needs_approval",
            "blocked",
            "invalid",
            "does not execute tasks",
            "does not grant permission",
            "explicit green-zone evidence",
        ):
            self.assertIn(statement, spec)

        for statement in (
            "PR126 adds `local-task-approval-gate/v1`",
            "Approval state in PR126 is advisory and non-effective",
            "must not introduce an executor",
        ):
            self.assertIn(statement, pr_spec)

        self.assertIn("local_task_approval_gate", matrix)
        self.assertIn("approval gate read-only", matrix)
        self.assertIn("não autoriza execução", matrix)
        self.assertIn("PR126 local task approval gate", alpha)
        self.assertIn("não concede permissão", alpha)

    def test_pr126_local_task_approval_gate_is_indexed_as_implemented(self) -> None:
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        matrix = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")

        self.assertIn("[Local task approval gate](local_task_approval_gate.md)", index)
        self.assertIn("[PR126](pr_126_local_task_approval_gate.md)", matrix)
        self.assertIn("tests/test_local_task_approval_gate.py", matrix)
