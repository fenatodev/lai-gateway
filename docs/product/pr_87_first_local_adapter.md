# PR 87 — first local adapter

## Objetivo

Adicionar o primeiro adapter real mínimo do LAI sem abrir capacidades externas.

O adapter escolhido é `local_status`, um handler interno e in-process para provar
que o dispatcher consegue executar uma capability governada sem recorrer a shell,
rede, credenciais, filesystem ou serviços externos.

## Escopo

Inclui:

- registro do adapter `local_status` no registry governado;
- capabilities allowlisted `local_status.status` e `local_status.echo`;
- handler interno em `lai_gateway/local_status_adapter.py`;
- integração com `adapter-dispatcher`;
- testes de registry, dispatcher, CLI e endpoint.

Não inclui:

- browser real;
- n8n real;
- MCP tool call real;
- voz, áudio ou microfone;
- leitura ou escrita de documentos;
- shell/subprocess;
- rede;
- credenciais.

## Modelo de segurança

`local_status` é real apenas no sentido de executar código Python local já
registrado no pacote. Ele não é uma ponte genérica para ferramentas.

Invariantes obrigatórias:

- `executes_tools=false`;
- `network_access=false`;
- `credential_access=false`;
- `filesystem_read=false`;
- `filesystem_write=false`;
- `shell_execution=false`;
- `external_side_effects=false`;
- `grants_permission=false`.

A capability concedida não eleva outros adapters. O dispatcher só executa se:

1. o adapter for `local_status`;
2. a capability estiver na allowlist;
3. a decisão de permissão for `allow`;
4. `--dispatch` ou `dispatch=true` for solicitado explicitamente.

## Risco principal

O risco é confundir adapter real mínimo com liberação geral de execução. Por isso
este PR mantém os outros adapters sem handler real e sem dispatch.

## Critério de aceite

- `local_status` aparece no registry como handler local;
- `adapter-dispatcher` executa somente `local_status.*` allowlisted;
- requests para browser/n8n/voice/document/mcp continuam não despachadas;
- payloads não expõem texto bruto de action nem valores de parâmetros;
- suíte completa passa.
