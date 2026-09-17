# LAI — documentação de produto

Índice canônico pós-PR90. O LAI busca ser um sistema operacional pessoal de IA local, open-source-first e modular. Direção de produto não é evidência de capacidade operacional.

## Documentos atuais

- **guia operacional público** — [Quickstart](../quickstart.md): instalação local source-first, diagnóstico e primeiro uso restrito.
- **checklist operacional público** — [Release checklist](../release_checklist.md): verificação source-only de versão, commit, CI e gates locais.
- **checklist operacional público** — [Local clean dogfood](../local_clean_dogfood.md): validação local reproduzível do alpha técnico sem capacidades externas.
- **guia visual público** — [Workbench visual guide](../workbench_visual_guide.md): mapa sanitizado do Workbench, Governance e `local_status`.
- **normativo** — [Roadmap](roadmap.md): sequência normativa pós-PR89 até PR100, dependências e gates.
- **normativo** — [Roadmap pós-PR100](post_pr100_roadmap.md): próximas trilhas após o alpha técnico, sem habilitar capacidades externas automaticamente.
- **normativo** — [Plano operacional pós-PR110](post_pr110_operating_plan.md): sequência PR111–PR120 para alpha operacional local antes de expansão externa real.
- **normativo** — [Project workspace contract](project_workspace_contract.md): contrato de raiz explícita, escopo local, dados tocados e exclusões antes de contexto/execução.
- **contrato funcional** — [Objective state](objective_state.md): estado read-only de objetivo, tarefas e checkpoints dentro de workspace explícito.
- **contrato funcional** — [Action proposal](action_proposal.md): proposta unificada read-only antes de aprovação, grant ou execução.
- **contrato funcional** — [Approval inbox](approval_inbox.md): caixa local de aprovações pendentes sanitizadas, sem autorização efetiva.
- **contrato arquitetural** — [Local operator](local_operator.md): `local-operator-spec/v1` para coordenação local futura; specified, not implemented; sem executor, shell, grants ou mudança de permissões.
- **contrato arquitetural** — [Local task format](local_task_format.md): `local-task-format/v1`, `local-task/v1` e `local-task-outbox/v1` para tarefas locais futuras; specified, not implemented; sem executor, shell, grants ou mudança de permissões.
- **implementação read-only** — [Local task dry-run](local_task_dry_run.md): `local-task-dry-run/v1` renderiza `local-task/v1` e `local-task-outbox/v1` sem executor, shell, grants, Harness, tools, adapters, credenciais ou efeitos externos.
- **implementação local governada** — [Local task file pack](local_task_file_pack.md): `local-task-file-pack/v1` planeja ou escreve registros JSON `local-task/v1` e `local-task-outbox/v1` sob `.lai-ai/tasks` e `.lai-ai/outbox`, sem executor, shell, Harness, tools, adapters, grants, credenciais ou efeitos externos.
- **gate read-only** — [Local task review gate](local_task_review_gate.md): `local-task-review-gate/v1` valida arquivos `local-task/v1` e `local-task-outbox/v1` antes de qualquer runner futuro; sem executor, shell, Harness, tools, adapters, grants, credenciais ou efeitos externos.
- **gate read-only** — [Local task approval gate](local_task_approval_gate.md): `local-task-approval-gate/v1` classifica uma revisão de tarefa local como `ready_without_approval`, `needs_approval`, `blocked` ou `invalid`; sem executor, shell, Harness, tools, adapters, grants, credenciais, mensagens, publicação, merge ou efeito externo.
- **contrato funcional** — [Dev loop fixture](dev_loop_fixture.md): fixture local Observe/Work/Review/Apply sem execução operacional.
- **contrato funcional** — [Context pack](context_pack.md): pacote explícito de contexto local por tarefa sem autoridade implícita.
- **contrato funcional** — [Model runtime profile](model_runtime_profile.md): perfil UX read-only de modelo local sem gerenciar runtime.
- **contrato funcional** — [Public browser inspector](public_browser_inspector.md): source inspector público restrito sem browser autenticado, cookies, JS, formulários, downloads ou link-following.
- **contrato funcional** — [External capability gate](external_capability_gate.md): gate read-only de primeira capacidade externa candidata sem habilitar execução.
- **matriz de estado, descritivo** — [Implementation matrix](implementation_matrix.md): maturidade, evidência e disponibilidade ao usuário.
- **prontidão alpha, critérios normativos** — [Alpha readiness](alpha_readiness.md): limitações conhecidas e decisão go/no-go.
- **descritivo, consolidação de revisão externa** — [Consolidação das revisões](roadmap_review_consolidation.md): insumos externos, decisões aceitas e adiadas.
- **normativo** — [Padrão de produto](lai_product_standard.md): princípios de produto.
- **normativo** — [Decisões arquiteturais](lai_architecture_decisions.md): separação de domínio, canal, autonomia e capacidade; contratos de direção, não comprovação de execução.

## Precedência documental

Para sequência prevalece o roadmap; para estado atual, a matriz; para publicação, os critérios de readiness. Contratos arquiteturais não concedem autoridade nem substituem evidência de runtime. As políticas do repositório continuam aplicáveis. Revisões externas e specs históricas não sobrepõem os documentos normativos atuais; em conflito sobre implementação, conferir código/testes e corrigir a matriz, sem inferir capacidades de uma intenção normativa.

## Histórico e insumos

Os documentos `pr_*.md` têm rótulo **spec de PR / histórico**: são registros históricos do escopo e da aceitação de cada PR; não são orientação operacional atual nem prova de maturidade posterior. Nenhum histórico foi removido.

- **histórico** — [Fila antiga](lai_next_prs.md): histórica, substituída pelo roadmap.
- **revisão externa / histórico** — [Revisão Astra](astra_architecture_review.md) e [revisão Codex/Astra](codex_astra_architecture_review.md): insumos históricos, sem autoridade automática.
- **descritivo / insumo de revisão externa** — [Prompt de revisão](roadmap_review_prompt.md): instrumento de coleta, não decisão.
- **spec de PR / histórico** — [PR89](pr_89_roadmap_alpha_readiness.md): baseline histórico da consolidação.
- **spec de PR / atual** — [PR120](pr_120_external_capability_gate.md): gate read-only que seleciona `browser.public_source_inspection` sem liberar browser autenticado, n8n real, MCP amplo ou mensagens.
- **spec de PR / histórico** — [PR119](pr_119_public_browser_v2.md): source inspector público restrito sem browser autenticado, cookies, JS, formulários, downloads ou link-following.
- **spec de PR / histórico** — [PR118](pr_118_model_runtime_profile.md): perfil UX read-only do modelo local sem baixar/iniciar runtime, probe automático, grants ou execução.
- **spec de PR / histórico** — [PR117](pr_117_context_pack.md): context pack local explícito sem grants, dispatch, credenciais, embeddings obrigatórios, varredura ampla ou execução.
- **spec de PR / histórico** — [PR116](pr_116_dev_loop_fixture.md): fixture local de dev loop sem grants, dispatch, credenciais, mensagens, publicação, merge ou execução.
- **spec de PR / histórico** — [PR115](pr_115_approval_inbox.md): caixa local de aprovação pendente sem grants, dispatch, credenciais, mensagens, publicação ou execução.
- **spec de PR / histórico** — [PR114](pr_114_action_proposal.md): proposta unificada read-only sem autorização efetiva, grants, dispatch ou execução.
- **spec de PR / histórico** — [PR113](pr_113_objective_state.md): leitura read-only de objetivo, tarefas e checkpoints sem grants, execução ou ingestão implícita.
- **spec de PR / histórico** — [PR112](pr_112_project_workspace_contract.md): contrato de workspace de projeto com raiz explícita e sem HOME scan ou ingestão implícita.
- **spec de PR / histórico** — [PR111](pr_111_operating_objective_plan.md): plano operacional pós-PR110 para avançar o LAI sem liberar capacidades externas.
- **spec de PR / histórico** — [PR110](pr_110_external_expansion_gate.md): gate read-only de expansão externa com go/no-go, matriz e evidência runtime sem habilitar capacidades externas.
- **spec de PR / histórico** — [PR109](pr_109_permission_ux.md): UX de permissões read-only separando intenção, decisão, autorização efetiva, grant e execução.
- **spec de PR / histórico** — [PR108](pr_108_n8n_minimal_governed.md): n8n mínimo governado como plano local por digest, grant single-use e sem execução real de workflow.
- **spec de PR / histórico** — [PR107](pr_107_mcp_minimal_governed.md): MCP mínimo governado com uma tool local não sensível, grant single-use e bloqueio de replay.
- **spec de PR / histórico** — [PR106](pr_106_public_browser_readonly.md): browser público read-only, sem autenticação, cookies, formulários ou automação JS.
- **spec de PR / histórico** — [PR105](pr_105_operational_local_model.md): modelo local operacional com configuração e diagnóstico sem gerenciar runtime.
- **spec de PR / histórico** — [PR104](pr_104_onboarding_ux_next_steps.md): onboarding/UX com próximos passos sanitizados no Workbench.
- **spec de PR / histórico** — [PR103](pr_103_clean_local_dogfood.md): dogfood local limpo com script/checklist reproduzível.
- **release notes / atual** — [v0.1.35](../releases/v0.1.35.md): nota source-first do alpha técnico, com limites públicos.
- **spec de PR / histórico** — [PR102](pr_102_release_alpha_technical.md): preparação source-first de tag/release alpha técnico, sem mudança funcional.
- **spec de PR / histórico** — [PR101](pr_101_post_pr100_roadmap.md): roadmap pós-PR100, sem mudança funcional nem publicação.
- **spec de PR / histórico** — [PR100](pr_100_technical_alpha_readiness.md): alpha público técnico com verificação `alpha-readiness/v1` e go/no-go read-only.
- **spec de PR / histórico** — [PR99](pr_99_workbench_local_documents.md): Workbench para documentos locais com seleção metadata-only e inspeção restrita.
- **spec de PR / histórico** — [PR98](pr_98_restricted_document_text.md): `document_text_local` restrito para `.txt/.md/.json` em workspace explícito.
- **spec de PR / histórico** — [PR97](pr_97_local_memory_context.md): memória local mínima por projeto/pessoal, com limites, exclusão de segredos e sem autoridade.
- **spec de PR / histórico** — [PR96](pr_96_local_model_chat_health_fallback.md): primeira conversa local-model-first, health e fallback explícito.
- **spec de PR / histórico** — [PR95](pr_95_authorization_recovery.md): persistência, expiração, revogação, consumo único e restart recovery para `local-status-read`.
- **spec de PR / histórico** — [PR94](pr_94_local_non_dry_run_authorization.md): autorização efetiva estreita para `local_status.status`.
- **spec de PR / histórico** — [PR93](pr_93_testable_identity.md): vínculo local testável de identidade usuário/cliente/agente/serviço.

GPT-6/Astra, Claude e Codex são revisores. Recomendações precisam de confronto com código, testes e decisão humana versionada. Documentos antigos fora desta lista devem ser lidos no contexto da versão e do escopo em que foram escritos.
- [Local task green executor](local_task_green_executor.md) — implemented PR127 bounded executor for green-zone local task commands.
