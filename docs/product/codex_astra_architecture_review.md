# codex astra architecture review

## origem

Revisao recebida em 2026-09-14 apos auditoria com Codex e Astra.

## sintese

A revisao identifica que o plano do LAI esta correto na direcao geral, mas ainda mistura constatacoes estaticas, garantias de seguranca e decisoes arquiteturais. A conclusao principal e que o projeto deve fechar contratos de identidade, autorizacao, lifecycle de acao, persistencia e contencao real antes de expandir skills, browser, n8n, voz e model lab.

## pontos criticos adotados

1. Evidencia de seguranca precisa ser qualificada. Ter guardrails, testes ou imagem fixada por digest nao prova isolamento efetivo.
2. O harness nao pode virar novo monolito. Conversa pessoal nao deve depender de workspace, run ou permissoes de execucao dev.
3. O envelope de acao nao pode carregar autoridade autodeclarada. Capacidades solicitadas sao entrada nao confiavel; capacidades concedidas sao resultado da politica.
4. Identidade precisa separar usuario, cliente, agente e servico. Aprovacoes devem ser vinculadas ao responsavel correto.
5. ASK encerrar o run pode ser seguro. A lacuna real e nao existir um percurso completo e verificavel ate a execucao autorizada.
6. Memoria pessoal e memoria de projeto precisam de isolamento. Conteudo recuperado nao pode virar autorizacao.
7. Instrucoes maliciosas em documentos, codigo e respostas de ferramentas devem ser tratadas como risco de prompt injection.
8. Shell local com efeitos nao pode ser tratado como apenas leitura por declaracao de perfil.
9. Revisao, promocao, aplicacao e publicacao devem ser termos distintos na interface, autorizacao e documentacao.
10. Conversa sem ferramentas pode entrar cedo. Contencao do shell local deve anteceder migracoes amplas de envelopes.

## impacto na fila de prs

A fila passa a priorizar contratos, conversa direta e contencao real antes de adapters grandes.

1. pr 61: contratos arquiteturais, identidade, autorizacao e lifecycle.
2. pr 62: conversation-first routing sem harness para mensagens comuns.
3. pr 63: contencao do shell local e mediação obrigatoria da tool layer.
4. pr 64: skills registry minimo com capacidades solicitadas, nao concedidas.
5. pr 65: dev controlado com sandbox, review, apply, expiracao e consumo unico.
6. pr 66: primeiro adapter governado, pequeno e testavel.

## regra nova

Nenhum modulo, skill, adapter, modo, canal ou dominio pode elevar permissao por conta propria. A autorizacao e sempre emitida pela policy central e registrada no lifecycle da acao.
