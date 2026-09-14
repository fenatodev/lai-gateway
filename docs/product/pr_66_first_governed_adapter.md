# PR 66 — primeiro adapter governado

## objetivo

Registrar o primeiro adapter governado do LAI sem habilitar execução externa.

## escopo

- Criar registry read-only de adapters governados.
- Registrar MCP como primeiro adapter porque já existe superfície de status/tools/policy-check.
- Explicitar que adapter não concede permissão.
- Explicitar que MCP tool execution permanece negado.
- Expor inspeção via CLI e endpoint do Gateway.

## fora de escopo

- Não executar MCP tools.
- Não criar browser adapter.
- Não criar n8n adapter.
- Não integrar SaaS.
- Não alterar permissões do sistema.

## contrato

Adapter declara superfície, capacidades solicitadas e riscos. O permission engine/tool layer decide autorização. Adapter não eleva canal, skill ou usuário.
