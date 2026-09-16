# PR105 — modelo local operacional

## Escopo

Implementar diagnóstico e configuração local mínima para runtime OpenAI-compatible no LAI Gateway. O objetivo é reduzir fricção para conectar um modelo local já instalado, sem transformar o Gateway em gerenciador de runtime.

## Contrato

- Domínio: modelo local operacional.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: configuração explícita pelo usuário e diagnóstico read-only.
- Capacidade: `model-runtime/v1`.

## Entrega

- Comando `lai-gateway model-runtime` com ações `show`, `configure` e `diagnose`.
- Endpoint protegido `/v1/gateway/model-runtime`.
- Painel "Modelo operacional" no Workbench.
- Configuração persistida localmente com `base_url`, `model_name` e caminho de arquivo de chave; o valor da chave nunca é persistido no JSON.
- Próximos passos acionáveis para endpoint, nome de modelo, chave local e probe OpenAI-compatible.

## Limites

- Sem download automático; marcador normativo: sem download automático.
- Sem nuvem.
- Sem execução de tools; marcador normativo: sem execução de tools.
- Sem iniciar servidor persistente.
- Sem shell.
- Sem browser.
- Sem n8n.
- Sem MCP tool execution.
- Sem publicação, tag ou release.
- Sem expor tokens, Bearer, prompt ou valor de chave.
- Configuração ou modelo não concede autoridade, aprovação, capability ou permissão.
