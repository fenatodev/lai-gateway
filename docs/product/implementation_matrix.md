# LAI implementation matrix

Estado pós-PR89 consolidado no PR90. Escopo: lai-gateway; capacidades do Harness não são automaticamente capacidades dos adapters do Gateway. [Índice](index.md) e [roadmap](roadmap.md).

## Legenda e evidência

- implemented / implementado: código e testes para o escopo descrito; não significa produto completo nem CI atual comprovada por este documento.
- experimental: caminho funcional estreito, sem promessa pública ampla.
- contract / contrato: interface ou declaração; execução real ausente ou bloqueada.
- simulated / simulado/dry-run: simulação sem executar a capability proposta.
- planned / planejado: trabalho futuro; blocked/deferred indicam dependência ou adiamento.
- Disponível ao usuário: coluna independente da maturidade; CLI/UI de inspeção não equivale a executor disponível.

Read-only declarado representa intenção; read-only simulado não prova contenção; read-only efetivamente imposto exige restrições do executor e testes negativos no escopo citado. Não extrapolar garantias entre adapters ou canais.

## Matriz

| Área | Estado | Disponível ao usuário | Evidência atual / limite | Próximo marco |
| --- | --- | --- | --- | --- |
| arquitetura core | contract | Documentação | Princípios e envelopes não provam execução | Manter quatro eixos separados |
| conversation-first | implemented | Chat conforme configuração | Roteamento comum sem run automático no Harness | PR96 primeira conversa |
| Workbench 3 modos | experimental | UI local | Observar/Trabalhar/Aplicar; não concede autorização ampla | PR92 guia visual |
| dev assistido | experimental | Local-chat com Harness compatível | Sandbox/review/promotion dependem do Harness; promoção não é publicação | Preservar limites |
| skills registry | implemented | Metadados/inspeção | Registry mínimo, declarações não concedem permissões | Expansão por spec |
| permission decision / policy evaluator | implemented | CLI/API de avaliação | Classificação por capability, não contenção universal | PR94 vínculo ao executor |
| identidade usuário/cliente/agente/serviço | contract | Campos/metadados | Rótulos de ator não provam identidade autenticada ponta a ponta | PR93 vínculo e rejeição de falsificação |
| authorization record / capture / validation | implemented | CLI/API/UI restritos | Envelope e intenção validados sem autoridade geral | PR94 e PR95 |
| effective authorization | experimental | Inspeção CLI/API/UI | Apenas adapter-dry-run; adapter_capability_authorized=false; authorization_persisted=false | PR94 autorização real não-dry-run |
| adapter dry-run | simulated | CLI/API/UI | Simulação implementada, sem execução da capability | Não usar como prova de efeito real |
| audit events | implemented | Metadados | Eventos derivados; não provam execução nem identidade | Correlacionar com ação real |
| persisted audit log | experimental | Operação local escopada | JSONL sanitizado; não prova integridade inviolável ou recovery de autorizações | PR95 evidência de recuperação |
| adapter dispatcher | experimental | CLI/API/UI restritos | Allowlist; caminho local_status separado da autorização efetiva dry-run | PR94 cadeia real delimitada |
| local_status adapter | experimental | Dispatch explícito local | Handler Python real status/echo; sem shell, filesystem, rede ou credenciais | Smoke seguro, não aprovação geral |
| persistência e restart recovery de autorização | planned | Não na cadeia geral de adapters | Expiração, revogação, consumo único e antirreplay ainda exigem prova conjunta | PR95 testes de falha/reinício |
| model local | experimental | Probes/chat conforme runtime | Não implica instalação guiada ou fallback garantido | PR96 |
| memory_context | planned | Não como store consolidado | Contexto pessoal/projeto ainda sem entrega mínima consolidada | PR97 |
| document/media | contract | Metadados | Sem processamento real por esses adapters | PR98–99 texto local; mídia adiada |
| browser | contract | Inspeção de contrato | Sem navegação real pelo adapter | Depois dos gates PR93–95 e spec própria |
| n8n | contract | Inspeção de contrato | Sem workflow/activation real pelo adapter | Depois dos gates PR93–95 |
| voice | contract | Metadados | Sem captura/voz operacional | Canal futuro |
| MCP execution | contract | Metadata/policy-check | Sem execução ampla de tools | Depois dos gates PR93–95 |
| Telegram outbound | experimental | CLI operacional opt-in | Envio real com destino configurado e enable-send; fora da cadeia geral de aprovação | Consentimento explícito por conteúdo/destino em novo fluxo |
| Telegram inbound | planned | Não como agente de conversa | Descoberta operacional não é agente inbound autorizado | Spec de canal restrito |
| social/career | contract | Metadados | Sem publicação, envio ou candidatura pelos adapters | Drafts futuros; efeitos bloqueados |
| Model Lab / Scout | contract | Diagnósticos parciais | Probes/eval e contratos não equivalem a plugins completos | Escopo e evidência próprios |
| instalação pública | planned | Scripts locais existentes | Quickstart reproduzível e empacotamento mínimo ainda precisam de evidência | PR91–92 |
| release alpha | planned | Não consolidada | CI e documentação não autorizam publicação | PR100 go/no-go |

## Limites de autorização

Em `effective_authorization.py`, o único escopo efetivo é `adapter-dry-run`. Em `adapter_dispatcher.py`, local_status usa decisão allow + capability allowlisted + dispatch explícito; não depende da autorização efetiva geral. A confirmação da UI não comprova aprovação durável no backend. Não promover esse caminho a prova de autorização real ampla.

Telegram outbound exige `LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1`, configuração e chamada operacional explícita. Essa habilitação não é aprovação persistente por mensagem, nem permissão para social/career. Novos envios governados continuam bloqueados até seus gates.

Toda mudança funcional deve atualizar estado, disponibilidade, evidência e limite da área afetada. Os PRs históricos descrevem seu momento, não ampliam a garantia atual.
