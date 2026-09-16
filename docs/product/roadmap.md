# LAI roadmap

## Status e direção

Fonte normativa pós-PR89, consolidada no PR90. [Índice canônico](index.md), [estado atual](implementation_matrix.md) e [alpha readiness](alpha_readiness.md) delimitam sua interpretação. A sequência antiga permanece histórica.

Objetivo: sistema operacional pessoal de IA local, open-source-first e modular. Separar domínio, canal, autonomia e capacidade: mudar canal ou domínio nunca concede execução. Cada PR declara objetivo, dimensão afetada, estado anterior/novo, risco, gate e evidência. Estados e disponibilidade são definidos na matriz; roadmap não habilita capacidades.

## Base preservada

PR61–73: contratos, conversation-first, mediação de ferramentas, skills, dev controlado e contratos de adapters. PR74–88: decisão/policy, envelopes, simulação, captura/validação, autorização estreita, auditoria local, dispatcher e Workbench. PR89: primeira consolidação de roadmap e readiness. Isso não comprova autorização geral nem integrações externas prontas.

## Sequência pós-PR89

| PR | Entrega | Gate de saída |
| --- | --- | --- |
| PR90 | Consolidação das revisões externas e promessa pública | Índice, matriz, readiness, README e testes documentais coerentes; sem mudança funcional |
| PR91 | Quickstart público mínimo e diagnóstico de instalação | Instalação limpa reproduzível, empacotamento mínimo identificado, pré-requisitos e falhas de Harness/token/modelo documentados |
| PR92 | Release checklist + guia visual mínimo do Workbench | Versão/artefato identificáveis, fluxo local_status explicado e evidência visual sanitizada |
| PR93 | Identidade testável usuário/cliente/agente/serviço | Testes de vínculo ao principal, origem confiável e rejeição de identidade falsificada, troca de cliente ou serviço |
| PR94 | Autorização efetiva para uma ação real local não-dry-run (authorization non-dry-run) | Ação/recurso/alvo/escopo exatos; revalidação no executor; casos positivos e negativos; nenhuma autoridade externa |
| PR95 | Persistência, expiração, revogação, consumo único e restart recovery | Recuperação após reinício, concorrência/replay e bloqueio contra duplicação de efeito; resultado desconhecido sem retry automático |
| PR96 | Modelo local, primeira conversa, health e fallback | Conversa sem run dev implícito; indisponibilidade explícita; fallback sem nuvem ou elevação de permissão automática |
| PR97 | memory_context local mínimo por projeto e contexto pessoal básico | Isolamento de contextos, limites e exclusão de segredos; memória não concede autoridade |
| PR98 | document_text_local restrito | Texto local em escopo permitido, limites, caminhos seguros e conteúdo tratado como não confiável |
| PR99 | Workbench para documentos locais | Seleção/inspeção restritas, estado e limites visíveis; sem envio externo |
| PR100 | Alpha público técnico | Todos os critérios go/no-go comprovados, instalação limpa, versão inequívoca e ausência de overclaiming |

PR94 prova somente uma ação local delimitada. `local_status` já executa um handler in-process, mas não substitui a prova de autorização non-dry-run. PR95 deve testar a mesma cadeia com reinício e falhas, não apenas persistir JSON. Persistência de audit log não equivale a persistência de aprovação.

## Capacidades externas — após os gates

Browser/n8n/MCP/social reais ficam depois de PR93, PR94 e PR95, fora da sequência até PR100. Também exigem specs e evidência específicas; concluir esses PRs não habilita integrações automaticamente.

Continuam bloqueados na expansão governada: browser autenticado, n8n activation, MCP tool execution amplo, publicação, envio de mensagens, candidaturas, formulários, automações externas e uso de credenciais. Browser público de leitura também exige contenção demonstrada; o rótulo read-only não basta. Voz, mídia, Model Lab e Scout continuam direção futura, sem promessa operacional ampla.

Telegram outbound operacional já existe fora da nova cadeia geral: somente acionamento explícito do operador, destino configurado e envio habilitado. Não é autorização para agentes enviarem mensagens. Exigir aprovação explícita de conteúdo e destino para qualquer novo fluxo; não afirmar que o CLI atual possui aprovação durável por mensagem.

## Evidência e dependências

Ordem obrigatória: documentação → quickstart/empacotamento → identidade testável → autorização real não-dry-run → persistência/restart/recovery → experiência local → alpha técnico. Capacidades externas dependem dos gates anteriores e de revisão própria.

Read-only declarado é intenção de contrato; simulado/dry-run não executa o efeito; efetivamente imposto exige contenção no executor e testes negativos específicos. Inspeção, logs ou CI isoladamente não provam ausência de efeitos.

## Revisões externas

GPT-6/Astra, Claude e Codex são revisores, não são autoridade automática. Os pontos recebidos são insumos críticos registrados na [consolidação](roadmap_review_consolidation.md). A direção é decidida por revisão humana versionada, confrontada com evidência local; nenhum parecer libera execução ou publicação.
