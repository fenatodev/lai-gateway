# PR115 — Approval inbox

## Objetivo

Adicionar `approval-inbox/v1` como caixa local de aprovações pendentes, persistida e sanitizada, para conectar proposta de ação e aprovação humana futura sem criar autorização efetiva.

## Escopo

- Novo módulo `approval_inbox`.
- CLI `approval-inbox`.
- API protegida `/v1/gateway/approval-inbox`.
- Workbench com painel mínimo para listar e enfileirar pendências.
- Documentação, matriz, readiness e testes.

## Fora de escopo

- Não habilita browser autenticado.
- Não ativa n8n real.
- Não chama MCP amplo.
- Não usa credenciais.
- Não envia mensagem.
- Não publica.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não chama Harness.
- Não executa tool.
- Não realiza efeito externo.

## Critério de aceitação

- `show` lista pendências sem escrita.
- `enqueue` persiste somente proposta pronta e sanitizada em workspace explícito.
- Conteúdo com formato de segredo é bloqueado.
- Saída JSON/texto não vaza token, segredo, prompt bruto sensível ou caminhos fora do escopo.
- Testes provam que inbox não concede autoridade nem executa capacidades.
