# PR107 — MCP mínimo governado

## Escopo

PR107 implementa `mcp-local-tool/v1`: uma única tool MCP local não sensível, `mcp.local_echo_digest`, sob escopo `mcp-local-safe-tool`.

Separação obrigatória:

- domínio: `tools`;
- canal: `gateway`, `workbench` e `cli`;
- autonomia: `governed_local_safe_tool`;
- capacidade: somente `mcp.local_echo_digest`;
- executor: handler local in-process do Gateway, sem chamar broker MCP externo;
- dados tocados: somente digest SHA-256 público e estado local de autorização append-only;
- efeito externo: nenhum.

## Contrato de autorização

A execução exige capability exata, escopo mínimo, identidade verificada, grant persistido de uso único e bloqueio de replay.

O fluxo permitido é:

1. planejar sem execução;
2. emitir grant local de autorização;
3. consumir o grant exatamente uma vez;
4. executar o handler local somente se o consumo liberar dispatch.

Mudança de identidade, action ou parâmetros quebra o consumo por hash. Conteúdo de ferramenta, memória, documento, browser ou modelo não concede autorização.

## Limites explícitos

- Sem `mcp.call_tool` amplo.
- Sem broker MCP externo para execução.
- Sem credenciais.
- Sem shell.
- Sem filesystem read/write fora do log local de autorização.
- Sem rede.
- Sem n8n.
- Sem browser.
- Sem formulários, publicação, envio de mensagens ou ações externas.
- Sem autorização por conteúdo recuperado.

## Testes

O PR deve provar execução positiva da tool local com grant single-use e testes negativos para replay, identidade forjada, parâmetro alterado, payload bruto e vazamento de segredo.
