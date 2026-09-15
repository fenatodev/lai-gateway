# LAI roadmap

## status

Documento normativo pós-PR88. Este roadmap substitui a fila operacional antiga como fonte de direção do `lai-gateway`, preservando o histórico dos PRs já concluídos.

## objetivo final

Levar o LAI a um sistema operacional pessoal de IA local, open-source-first e modular, com instalação reproduzível, Workbench utilizável, modelo local, memória local, dev assistido, automações governadas, documentos, mídia, browser, voz e integrações externas por adapters.

O objetivo não é liberar autonomia irrestrita. O objetivo é ampliar capacidade real sem perder separação entre domínio, canal, autonomia e capacidade.

## regra de direção

Todo PR pós-PR88 deve declarar:

```text
objetivo do roadmap atendido
dimensão tocada: domínio, canal, autonomia ou capacidade
estado alterado: contrato, experimental, implementado ou deferred
risco novo criado
gate que contém esse risco
```

PR que não melhora produto, segurança, instalação, documentação pública ou uma capacidade planejada deve ser tratado como suspeito.

## estados oficiais

```text
implementado: existe código, teste, CLI/endpoint/UI quando aplicável, e CI verde
experimental: existe caminho funcional restrito, ainda não pronto como promessa pública ampla
contrato: superfície declarada, sem execução real ou com execução bloqueada
planejado: aceito na direção, ainda sem contrato suficiente
deferred: válido, mas adiado por dependência, risco ou custo
fora_de_escopo: não pertence ao LAI atual
```

Nenhum texto de README, UI ou release deve vender como implementado algo que esteja em contrato, planejado ou deferred.

## trilho já concluído

```text
PR 61: contratos arquiteturais, identidade, autorização e lifecycle
PR 62: conversation-first routing
PR 63: contenção do shell e mediação obrigatória de ferramentas
PR 64: skills registry mínimo
PR 65: dev controlado
PR 66: primeiro adapter governado
PR 67: limpeza de warning no model run
PR 68-73: contratos de browser, n8n, voz, model lab, social/career e document/media
PR 74-81: decisão, policy, autorização, proposta, audit events, dry-run e visibilidade no Workbench
PR 82-88: captura, validação, autorização escopada, audit log, dispatcher, primeiro adapter local e UI segura
```

## próximos blocos de produto

### bloco 1: alpha publicável

Objetivo: permitir que outro usuário instale, rode e entenda o LAI sem depender de conversa privada.

```text
PR 89: consolidar roadmap e prontidão alpha
PR 90: alinhar README público, versão planejada e promessa real
PR 91: quickstart de instalação limpa com diagnóstico de pré-requisitos
PR 92: release checklist e critérios de tag alpha
PR 93: guia visual mínimo do Workbench e fluxo local_status
```

Critério de saída: o projeto pode ser publicado como alpha técnico sem prometer browser, n8n, voz ou automação externa reais.

### bloco 2: experiência local útil

Objetivo: fazer o LAI ser útil em tarefas locais antes de abrir capacidades externas.

```text
PR 94: modelo local como chat/health path de primeira execução
PR 95: memory_context local por projeto, sem segredos e com escopo
PR 96: document_text_local adapter para .txt, .md e .json dentro de escopo permitido
PR 97: Workbench para seleção/inspeção de documento local seguro
```

Critério de saída: usuário consegue instalar, abrir o Workbench, conversar com modelo local quando disponível e usar uma capacidade local útil sem rede externa.

### bloco 3: capacidades externas read-only primeiro

Objetivo: abrir capacidades externas apenas depois de gates locais e auditoria estarem claros.

```text
PR 98: browser_public read-only com allowlist de ações sem login, sem formulário e sem clique sensível
PR 99: n8n discovery local e workflow dry-run, sem ativar workflow
PR 100: MCP governed execution phase 1 para tools locais explicitamente allowlisted
```

Critério de saída: cada capacidade externa tem proposta, autorização, auditoria, bloqueio de segredos e modo read-only antes de qualquer side effect.

### bloco 4: interfaces humanas

Objetivo: ampliar canais sem elevar permissão.

```text
PR 101: voice push-to-talk local, sem wake word e sem executar ação automaticamente
PR 102: Telegram inbound limitado a conversa/status, sem criar run sensível por mensagem
PR 103: mobile Workbench hardening para leitura, pareamento e UX
```

Critério de saída: voz, Telegram e mobile operam como canais, não como autoridades.

### bloco 5: automação, social e publicação operacional

Objetivo: permitir ações externas com consentimento explícito, rastreabilidade e recuperação.

```text
PR 104: social/career drafts, sem publicação ou candidatura
PR 105: n8n activation approval gate, ainda sem credenciais novas automáticas
PR 106: browser authenticated session proposal, sem execução sem aprovação explícita por alvo
PR 107: release packaging e publicação alpha/beta
```

Critério de saída: ações externas são propostas, revisadas, autorizadas, executadas e auditadas; reinício não duplica side effects.

## ordem de dependência

```text
roadmap -> alpha docs -> install -> local useful capability -> browser/n8n/MCP read-only -> voice/telegram -> external side effects
```

Não inverter essa ordem sem registrar uma decisão arquitetural nova.

## regra para revisões externas

GPT-6, Codex e Astra podem revisar roadmap, lacunas, dependências e riscos. Eles não são autoridade automática. A fonte de verdade é este roadmap versionado no repo, depois de revisão humana.
