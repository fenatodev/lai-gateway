# PR99 — Workbench para documentos locais

## Escopo

PR99 cria `document-workbench/v1`: uma superfície de Workbench para seleção e inspeção restritas de documentos locais já cobertos por `document-text-local/v1`.

Não cria ingestão completa, indexação, embeddings, resumo automático, OCR, PDF, Office, mídia, upload externo, browser, n8n, MCP tool execution, HOME scan, glob recursivo ou confiança em conteúdo recuperado.

## Domínio, canal, autonomia e capacidade

- Domínio: documentos locais textuais restritos.
- Canal: Gateway API protegida e Workbench local.
- Autonomia: listar candidatos permitidos no topo de um workspace explícito e inspecionar um caminho relativo informado.
- Capacidade: seleção metadata-only e inspeção via `document-text-local/v1`, com limites visíveis.

## Mudança funcional

O Gateway expõe `/v1/gateway/document-workbench`. A rota lista apenas candidatos `.txt`, `.md` e `.json` no nível superior do `workspace_root` informado, sem leitura de conteúdo durante a listagem e sem busca recursiva. Quando `selected_relative_path` é informado, a inspeção delega para `document-text-local/v1`.

A UI ganha estado explícito de documentos: botão para listar candidatos permitidos, seletor preenchido pelo backend, sincronização do caminho relativo e saída com limites/security flags. O painel continua separado de memória, modelo e dev assistido.

## Segurança preservada

- Conteúdo de documento é não confiável e nunca concede autoridade, aprovação, capability ou permissão.
- Listagem é metadata-only, não recursiva e limitada.
- Inspeção usa somente `.txt`, `.md` e `.json` em workspace explícito.
- Sem PDF, sem OCR, sem Office, sem mídia, sem rede, sem shell, sem tools, sem envio externo, sem upload externo e sem filesystem write.
- Seleção no Workbench não equivale a autorização nem a aprovação.

## Evidência

Testes cobrem listagem limitada, ausência de conteúdo na seleção, inspeção delegada, bloqueio de workspace fora do escopo, API/UI e documentação canônica.

Gate local: `PYTHON=python3 make check`.
