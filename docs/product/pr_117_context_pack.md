# PR117 — context pack local

## Objetivo

Adicionar `context-pack/v1` para montar contexto local explícito por tarefa, combinando objetivo, memória e documentos selecionados sem confiança implícita.

## Entrega

- Módulo `lai_gateway/context_pack.py`.
- CLI `lai-gateway context-pack`.
- API protegida `/v1/gateway/context-pack`.
- Card no Workbench para montar context pack local.
- Testes unitários, API/UI e documentação de produto.

## Restrições

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
- Não executa tools.
- Não escreve arquivos.
- Não escreve source checkout.
- Não faz HOME scan.
- Não faz varredura recursiva ampla.
- Não faz ingestão implícita.
- Não exige embeddings.
- Não gera embeddings.
- Não realiza efeito externo.

## Critérios de aceitação

- Contexto só é montado a partir de workspace explícito.
- Documentos precisam ser selecionados explicitamente e passam pelo leitor restrito existente.
- Memória é lida em modo `show`, sem persistência.
- Conteúdo retornado é marcado como não confiável e não concede autoridade.
- `make check` verde.
