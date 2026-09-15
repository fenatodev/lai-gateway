# PR 69: n8n adapter contract

## Objetivo

Registrar o n8n como adapter governado antes de qualquer criação, ativação ou execução real de workflow.

## Escopo

- adicionar `n8n` ao adapter registry;
- manter o adapter em modo `contract_only`;
- declarar capacidades solicitadas sem concedê-las;
- marcar execução de workflow, credenciais e efeitos externos como desabilitados;
- cobrir o contrato com testes.

## Fora de escopo

- instalar ou configurar n8n;
- conectar credenciais;
- criar, ativar ou executar workflows;
- expor webhooks públicos;
- enviar dados para serviços externos.

## Decisões

- n8n é motor de automação, não core do LAI;
- adapter não decide política;
- workflows com credenciais, webhooks ou efeitos externos exigem aprovação humana e policy check;
- inspeção/validação pode ser modelada antes de execução.

## Validação

- `tests/test_adapters.py` cobre o contrato `n8n`;
- `make check` deve passar sem execução externa.
