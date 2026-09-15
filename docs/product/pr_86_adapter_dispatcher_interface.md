# PR 86 — adapter dispatcher interface

## Objetivo

Criar a primeira interface de dispatcher para adapters governados do LAI, sem registrar handlers reais e sem executar adapters.

Este PR introduz somente um contrato avaliável de despacho. Ele permite observar se a cadeia de governança chegaria ao ponto de despacho, mas bloqueia qualquer execução real.

## Escopo

Inclui:

- módulo `lai_gateway.adapter_dispatcher`;
- objeto `AdapterDispatcherInterface`;
- CLI `lai_gateway adapter-dispatcher`;
- endpoint `GET /v1/gateway/adapter-dispatcher`;
- testes de bloqueio, escopo, segredo e endpoint.

Não inclui:

- browser real;
- n8n real;
- voz real;
- leitura/processamento real de documentos;
- chamada MCP real;
- handlers de adapter;
- credenciais;
- rede externa;
- execução de tool.

## Regras

A interface sempre publica:

- `interface_only=true`;
- `handler_registered=false`;
- `dispatch_enabled=false`;
- `dispatch_permitted=false`;
- `adapter_dispatched=false`;
- `adapter_executed=false`;
- `executes_tools=false`;
- `external_side_effects=false`.

Mesmo quando existe autorização efetiva para o escopo `adapter-dry-run`, a capability do adapter continua não autorizada.

## Estados esperados

- `planned_not_dispatched`: cadeia válida para observação, sem pedido de despacho.
- `pending`: falta autorização efetiva escopada.
- `blocked`: adapter ausente, escopo inválido, tentativa de dispatch real ou ausência de handler.

## Risco tratado

O risco principal é confundir a existência de um dispatcher com autorização para executar adapters. Este PR evita isso separando interface de despacho, handler registrado e permissão de despacho.

