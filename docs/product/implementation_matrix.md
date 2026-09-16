# LAI implementation matrix

Estado pós-PR89 consolidado no PR90. Escopo: lai-gateway; capacidades do Harness não são automaticamente capacidades dos adapters do Gateway. [Índice](index.md) e [roadmap](roadmap.md).

## Legenda e evidência

- implemented / implementado: código e testes para o escopo descrito; não significa produto completo nem CI atual comprovada por este documento.
- experimental: caminho funcional estreito, sem promessa pública ampla.
- contract / contrato: interface ou declaração; execução real ausente ou bloqueada.
- planned / planejado: trabalho futuro; blocked/deferred indicam dependência ou adiamento.
- Tipo de execução: metadados, simulado/dry-run, local restrito ou dependente de runtime; não é uma classificação de maturidade. Uma simulação pode estar implementada sem executar a capability proposta.
- Evidência: referências a contratos, módulos e testes; presença de teste não comprova execução recente nem garantia além do seu escopo.
- Disponível ao usuário: coluna independente da maturidade; CLI/UI de inspeção não equivale a executor disponível.

Read-only declarado representa intenção; read-only simulado não prova contenção; read-only efetivamente imposto exige restrições do executor e testes negativos no escopo citado. Não extrapolar garantias entre adapters ou canais.

## Matriz

| Área | Maturidade | Tipo de execução | Disponível ao usuário | Evidência | Limite conhecido | Próximo marco |
| --- | --- | --- | --- | --- | --- | --- |
| arquitetura core | contract | declaração | Documentação | [contrato](lai_architecture_decisions.md) | Princípios e envelopes não provam execução | Manter quatro eixos separados |
| conversation-first | implemented | chat local-model-first | Chat conforme configuração | [testes de UI](../../tests/test_ui.py) | Roteamento comum sem run automático no Harness; fallback local explícito quando modelo indisponível | PR97 memory_context |
| Workbench 3 modos | experimental | UI / integração | UI local | [UI](../../lai_gateway/static/app.js), [testes](../../tests/test_ui.py) | Observar/Trabalhar/Aplicar; não concede autorização ampla | PR92 guia visual |
| dev assistido | experimental | dependente do Harness | Local-chat com Harness compatível | [cliente](../../lai_gateway/harness_client.py), [testes](../../tests/test_harness_client.py) | Sandbox/review/promotion dependem do Harness; promoção não é publicação | Preservar limites |
| skills registry | implemented | metadados | Metadados/inspeção | [registry](../../lai_gateway/skills.py), [testes](../../tests/test_skills.py) | Registry mínimo, declarações não concedem permissões | Expansão por spec |
| permission decision / policy evaluator | implemented | classificação + identity gate | CLI/API de avaliação | [policy](../../lai_gateway/policy_evaluator.py), [identity](../../lai_gateway/identity.py), [testes](../../tests/test_identity.py) | Identidade não confiável bloqueia decisão; ainda não é contenção universal | PR94 vínculo ao executor |
| identidade usuário/cliente/agente/serviço | experimental | binding local testável | CLI/API de inspeção e policy gate | [módulo](../../lai_gateway/identity.py), [testes](../../tests/test_identity.py), [spec](pr_93_testable_identity.md) | Verifica origem local confiável, claims e drift; não é login completo nem autorização | PR94 autorização real delimitada |
| authorization record / capture / validation | implemented | validação sem execução | CLI/API/UI restritos | [validação](../../lai_gateway/authorization_validation.py), [testes](../../tests/test_authorization_validation.py) | Envelope e intenção validados sem autoridade geral | PR94 e PR95 |
| effective authorization | experimental | dry-run e local restrito | Inspeção CLI/API/UI | [módulo](../../lai_gateway/effective_authorization.py), [testes](../../tests/test_effective_authorization.py) | adapter-dry-run continua sem adapter capability; local-status-read só autoriza local_status.status; persistência fica em authorization-recovery | PR96 conversa local |
| adapter dry-run | implemented | simulado/dry-run | CLI/API/UI | [testes](../../tests/test_adapter_dry_run.py) | Simulação implementada, sem execução da capability | Não usar como prova de efeito real |
| audit events | implemented | metadados | Metadados | [testes](../../tests/test_audit_events.py) | Eventos derivados; não provam execução nem identidade | Correlacionar com ação real |
| persisted audit log | experimental | persistência local restrita | Operação local escopada | [testes](../../tests/test_persisted_audit_log.py) | JSONL sanitizado; não prova integridade inviolável ou recovery de autorizações | PR95 evidência de recuperação |
| adapter dispatcher | experimental | local restrito com grant | CLI/API/UI restritos | [dispatcher](../../lai_gateway/adapter_dispatcher.py), [testes](../../tests/test_adapter_dispatcher.py) | Dispatch local_status.status exige local-status-read efetivo e grant persistido de uso único; handler sem shell, rede, credenciais ou filesystem write | PR96 experiência local |
| local_status adapter | experimental | local restrito | Dispatch explícito local | [handler](../../lai_gateway/local_status_adapter.py), [testes](../../tests/test_adapter_dispatcher.py) | Handler Python real; autorização non-dry-run só cobre status, não echo; sem shell, filesystem, rede ou credenciais | Smoke seguro, não aprovação geral |
| persistência e restart recovery de autorização | experimental | JSONL local append-only | CLI/API/UI para cadeia local_status | [módulo](../../lai_gateway/authorization_recovery.py), [testes](../../tests/test_authorization_recovery.py) | Só `local-status-read`/`local_status.status`; não é autorização geral nem integração externa | PR96 primeira conversa |
| model local | experimental | endpoint local/private OpenAI-compatible | CLI/API/UI restritos | [módulo](../../lai_gateway/model.py), [testes](../../tests/test_model.py) | `model-chat` não cria Harness run, não usa nuvem, não executa tools, não instala runtime e não baixa modelo | PR98 documentos locais |
| memory_context | experimental | JSONL local escopado | CLI/API/UI restritos | [módulo](../../lai_gateway/memory_context.py), [testes](../../tests/test_memory_context.py), [spec](pr_97_local_memory_context.md) | Só notas explícitas; rejeita segredos; sem embeddings, captura automática, autorização ou confiança implícita | PR98 documentos locais |
| document/media | contract | metadados/contrato | Metadados | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem processamento real por esses adapters | PR98–99 texto local; mídia adiada |
| browser | contract | metadados/contrato | Inspeção de contrato | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem navegação real pelo adapter | Depois dos gates PR93–95 e spec própria |
| n8n | contract | metadados/contrato | Inspeção de contrato | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem workflow/activation real pelo adapter | Depois dos gates PR93–95 |
| voice | contract | metadados/contrato | Metadados | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem captura/voz operacional | Canal futuro |
| MCP execution | contract | metadados/contrato | Metadata/policy-check | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem execução de tools por esse adapter; apenas metadata/policy-check; executes_tools=false. | Depois dos gates PR93–95 |
| Telegram outbound | experimental | envio real opt-in | CLI operacional opt-in | [módulo](../../lai_gateway/telegram.py), [testes](../../tests/test_telegram.py) | Envio real com destino configurado e enable-send; fora da cadeia geral de aprovação | Consentimento explícito por conteúdo/destino em novo fluxo |
| Telegram inbound | planned | não disponível como agente | Não como agente de conversa | [roadmap](roadmap.md) | Descoberta operacional não é agente inbound autorizado | Spec de canal restrito |
| social/career | contract | metadados/contrato | Metadados | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Sem publicação, envio ou candidatura pelos adapters | Drafts futuros; efeitos bloqueados |
| Model Lab | contract | metadados/contrato | Inspeção do adapter model_lab | [registry](../../lai_gateway/adapters.py), [testes](../../tests/test_adapters.py) | Contrato de avaliação; diagnósticos reais de runtime estão na linha model local, não provam execução do adapter | Escopo e evidência próprios |
| Scout | contract | metadados de skill | Skill declarada no registry | [registry](../../lai_gateway/skills.py), [testes](../../tests/test_skills.py) | Declara network_research como capacidade solicitada; grants_permissions=false; não comprova pesquisa externa operacional | Execução futura sujeita a spec/policy |
| instalação pública | planned | scripts locais / guia planejado | Scripts locais existentes | [script](../../scripts/install-local.sh), [testes](../../tests/test_scripts.py) | Quickstart reproduzível e empacotamento mínimo ainda precisam de evidência | PR91–92 |
| release alpha | planned | não publicada por este PR | Não consolidada | [readiness](alpha_readiness.md) | CI e documentação não autorizam publicação | PR100 go/no-go |

## Restrições públicas

Browser, n8n, voz, execução real de tools MCP, social e automações externas governadas não estão disponíveis como funcionalidades prontas. Contratos e simulações não autorizam execução real.

## Limites de autorização

Em `effective_authorization.py`, os escopos efetivos continuam estreitos: `adapter-dry-run` para simulação e `local-status-read` somente para `local_status.status`. Em `authorization_recovery.py`, grants locais são persistidos, expiram, podem ser revogados e são consumidos uma vez antes do dispatch. Em `adapter_dispatcher.py`, dispatch real de `local_status.status` exige decisão allow, capability allowlisted, identidade verificada, escopo `local-status-read` e dispatch explícito. A confirmação da UI não comprova aprovação durável no backend. Não promover esse caminho a prova de autorização real ampla.

local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.

Telegram outbound exige `LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1`, configuração e chamada operacional explícita. Telegram outbound tem limite conhecido: não possui aprovação durável por mensagem. Essa habilitação não é permissão para social/career. Novos envios governados continuam bloqueados até seus gates.

Toda mudança funcional deve atualizar estado, disponibilidade, evidência e limite da área afetada. Os PRs históricos descrevem seu momento, não ampliam a garantia atual.
