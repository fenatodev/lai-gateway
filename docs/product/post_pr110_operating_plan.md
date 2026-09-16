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
| PR117 | Context pack local | Contexto explícito por tarefa | Memória/documentos/projeto selecionados explicitamente, sem confiança implícita, embeddings obrigatórios ou varredura ampla |
| PR118 | Modelo local operacional UX | Runtime profile UX | Perfil de modelo local visível, fallback e diagnóstico; sem baixar/iniciar runtime automaticamente |
| PR119 | Browser público v2 | Source inspector público restrito | GET público read-only ampliado por spec estreita; sem login, cookies, JS automation, formulários ou downloads |
| PR120 | Gate de primeira capacidade externa | Go/no-go por capacidade candidata | Escolha explícita de uma capacidade externa candidata; permanecer bloqueada se faltar executor, política, aprovação e testes negativos |

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
