# LAI post-PR110 operating plan

Plano normativo após o encerramento da trilha PR101–PR110. Ele não substitui o histórico; define a próxima sequência para aproximar o LAI do objetivo de sistema operacional pessoal de IA local, open-source-first e modular.

## Objetivo operacional

Transformar o alpha técnico em alpha operacional local: uma interface única que organiza conversa, contexto local, proposta, aprovação, execução segura, revisão, apply e auditoria sem promover capacidades externas antes de gates próprios.

O foco não é adicionar mais adapters sensíveis. O foco é tornar o fluxo local coerente, testável e reversível para uso diário no repo do usuário.

## Princípios obrigatórios

- Separar domínio, canal, autonomia e capacidade em cada incremento.
- Mensagem comum continua conversa direta; não cria run implícito no Harness.
- Conteúdo recuperado de memória, documento, web, modelo ou ferramenta não concede autorização.
- Skills, adapters e canais continuam incapazes de elevar permissão.
- Capacidade externa real exige spec própria, executor contido, testes negativos e aprovação humana separada.
- Telegram outbound existente permanece fora da cadeia geral de aprovação e não vira permissão ampla.
- PR110 permanece como no-go para browser autenticado, n8n real, MCP amplo, voz operacional, credenciais, publicação, formulários e mensagens governadas.

## Sequência recomendada PR111–PR120

| PR | Trilha | Entrega | Gate de saída |
| --- | --- | --- | --- |
| PR111 | Objetivo operacional | Plano pós-PR110 | Roadmap operacional versionado, índice/matriz atualizados e testes documentais sem mudança funcional |
| PR112 | Estado de projeto | Project workspace contract | Raiz explícita, escopo local, dados tocados, exclusões e ausência de HOME scan ou ingestão implícita |
| PR113 | Objetivos e tarefas locais | `objective-state/v1` | Registro local read-only de objetivo/tarefas/checkpoints, sem grants, adapters ou execução |
| PR114 | Proposta unificada | `action-proposal/v1` | Proposta implementada declara domínio, canal, autonomia, capacidade, alvo, dados, efeito e risco; sem autorização efetiva |
| PR115 | Caixa de aprovação | `approval-inbox/v1` | Aprovações pendentes persistidas e sanitizadas; sem grant, dispatch, execução ou efeito externo |
| PR116 | Loop dev local controlado | `dev-loop-fixture/v1` | Observe/Work/Review/Apply testado em fixture local, com evidência; sem browser autenticado, n8n real, MCP amplo, credenciais, mensagens, publicação, grants, adapter dispatch, Harness, tools, merge automático ou escrita no source checkout |
| PR117 | Context pack local | `context-pack/v1` | Memória/documentos/projeto selecionados explicitamente, sem confiança implícita, embeddings obrigatórios ou varredura ampla |
| PR118 | Modelo local operacional UX | `model-runtime-profile/v1` | Perfil de modelo local visível, fallback e diagnóstico; sem baixar/iniciar runtime automaticamente |
| PR119 | Browser público v2 | `public-browser-inspector/v1` | Source inspector público restrito; GET público read-only ampliado por spec estreita; sem login, cookies, JS automation, formulários, downloads ou link-following |
| PR120 | Gate de primeira capacidade externa | `external-capability-gate/v1` | Escolha explícita de `browser.public_source_inspection` como candidata read-only limitada; browser autenticado, n8n real, MCP amplo e mensagens seguem bloqueados se faltar executor, política, aprovação e testes negativos |

Após o PR120, PR121 propõe `local-operator-spec/v1` como follow-up documental: specified, not implemented; sem executor, shell, grants ou mudança de permissões; gateway classifica intenção/proposta e Harness executa dev controlado/review/apply.
Após o PR121, PR122 propõe `local-task-format/v1` como follow-up documental: specified, not implemented; define `local-task/v1`, `local-task-outbox/v1` e convenções `.lai-ai/tasks`, `.lai-ai/outbox`, `.lai-ai/logs` sem criar diretórios, executor, shell, grants ou mudança de permissões.
Após o PR122, PR123 implementa `local-task-dry-run/v1` como renderer read-only: produz `local-task/v1` e `local-task-outbox/v1` sem executor, shell, grants, Harness, tools, adapters, credenciais, mensagens, publicação, merge em `main` ou efeito externo.
Após o PR123, PR124 implementa `local-task-file-pack/v1`: planeja ou escreve registros JSON `local-task/v1` e `local-task-outbox/v1` sob `.lai-ai/tasks` e `.lai-ai/outbox`, sem executor, shell, Harness, tools, adapters, grants, credenciais, mensagens, publicação, merge em `main` ou efeito externo.
Após o PR124, PR125 implementa `local-task-review-gate/v1`: valida arquivos `local-task/v1` e `local-task-outbox/v1`, retornando ready/blocked/invalid sem executor, shell, Harness, tools, adapters, grants, credenciais, mensagens, publicação, merge em `main` ou efeito externo.

## Ordem e dependências

PR111 deve vir primeiro porque o roadmap pós-PR100 terminou no PR110. Sem novo plano, qualquer avanço vira expansão oportunista.

PR112 deve permanecer contrato antes de runtime: primeiro declara fronteira do projeto, depois PR113 lê objetivo/tarefas dentro dessa fronteira sem transformar conteúdo em autorização. PR112–PR118 devem consolidar o uso local antes de nova superfície externa. PR119 só pode ampliar browser público se a contenção continuar verificável. PR120 não libera uma capacidade externa; apenas escolhe e avalia a primeira candidata com critérios explícitos.

## Fora de escopo nesta sequência até gate próprio

- Browser autenticado.
- Uso de credenciais por agente.
- n8n activation ou execução real de workflow.
- MCP amplo ou execução externa de tools.
- Voz operacional com captura de microfone ou wake word.
- Envio governado de mensagens, publicação, candidatura, formulário ou compra.
- PDF/OCR/Office/mídia ampla, upload externo ou ingestão automática.
- Merge em `main`, tag, release ou anúncio sem aprovação humana na hora.

## Critério de mudança funcional

Qualquer PR funcional relevante deve começar por spec curta e declarar: domínio, canal, autonomia, capacidade, executor, dados tocados, efeito externo, política de autorização, teste positivo e testes negativos.

Para ações locais controladas, a autorização deve ser ligada a ação, alvo, parâmetros, validade, identidade e hash do conteúdo quando aplicável. Para ações externas ou irreversíveis, aprovação humana separada continua obrigatória mesmo que um gate técnico esteja verde.

## Risco principal

O risco atual não é falta de adapters; é confundir maturidade documental com capacidade operacional. A sequência prioriza estado, proposta, aprovação e contexto para evitar que o Gateway ou o Harness virem um monólito implícito de automação.
## PR126 — local task approval gate

PR126 coloca um gate read-only entre review de tarefa local e qualquer executor futuro. O estado de aprovação é advisory: não executa, não autoriza, não concede grant e não produz efeito externo. A próxima etapa segura é executor mínimo de zona verde, separado deste gate.

## PR127 — local task green executor

Add a minimal executor after PR126. It may run only green-zone, approval-gate-ready, task-declared, exact allowlisted local commands. It must not become a shell bridge or permission grant mechanism.

## PR128 — local task content binding

PR128 specifies `local-task-content-binding/v1` before any further expansion of
the local executor. `task_id` remains correlation only; reviewed task content
must be bound by a deterministic canonical digest propagated through review and
approval and recomputed before execution.

PR128 is documentation only. It does not add hashing runtime code, commands,
allowlist entries, grants, Harness calls, adapters, tools, credentials,
messages, publication, merge automation or external effects.

## PR129 — local task content binding runtime

PR129 implements `local-task-content-binding/v1` across review, approval and
the bounded green executor. Review emits the canonical `task_digest`, approval
validates and propagates it, and the executor recomputes it from the same task
used for command checks before execution.

Digest mismatch is invalid input and executes no command. PR129 does not expand
the PR127 exact-command allowlist, grant authority, change autonomy semantics,
enable arbitrary shell, call Harness, dispatch adapters/tools, use credentials,
send messages, publish or automate merge.

## PR130 — local operator runtime

PR130 implements `local-operator-runtime/v1` as the first end-to-end local
orchestration path over the already governed local-task components.

The runtime materializes the bounded task/file pack, runs review, classifies it
through the approval gate, preserves `task_digest` content binding and reaches
the PR127 green executor only for `ready_without_approval` green tasks.

PR130 does not add command allowlist entries, create arbitrary shell, grant
authority, change autonomy, call Harness for this path, dispatch adapters/tools,
use credentials, send messages, publish or automate merge.

## PR131 — Workbench local operator integration

PR131 implements `workbench-local-operator/v1` as a bounded Gateway/Workbench
surface over `local-operator-runtime/v1`.

The browser sends only one fixed profile identifier. The Gateway resolves the
LAI Gateway source checkout root and maps that profile to commands already
present in the PR127 exact allowlist.

The initial profiles cover repository status, diff validation, diff summary,
Python compile validation, local gate tests and the existing `make check`.

PR131 does not accept free-form commands or arbitrary repository roots from the
browser. It does not expand the PR127 allowlist, change autonomy semantics,
create grants, call Harness for this operator path, dispatch adapters/tools, use
credentials, send messages, publish, create PRs or automate merge.

## PR132 — Conversation-first governed development flow

PR132 implements `workbench-governed-dev-flow/v1` and aligns the main Workbench
composer with the architectural conversation boundary.

Observe sends normal conversation directly through `/v1/gateway/chat` and does
not create a Harness run.

Work is an explicit user choice and continues to use the existing local-chat
Harness path for isolated development, validation, event polling and review.

Apply does not create a new run. It operates only on the current review and
continues to require explicit confirmation before Harness promotion.

PR132 introduces no natural-language execution inference, shell, grant,
credential use, external action, Git publication, PR creation or merge
automation.


## PR133 — Direct conversation session

PR133 defines `direct-conversation-session/v1` as the next conversation-first
milestone after PR132.

Normal Observe conversation gains explicit bounded multi-turn session continuity
through the Gateway while remaining outside Harness execution.

Conversation history remains content, not authority. PR133 must not infer Work,
create implicit Harness runs, expand permissions, use credentials, publish,
create pull requests or automate merge.
