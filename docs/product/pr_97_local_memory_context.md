# PR97 — local memory_context mínimo

## Escopo

PR97 cria `memory-context/v1`: um store local mínimo para contexto por projeto e contexto pessoal básico. Ele serve para recuperar notas curtas e explícitas; não interpreta, não classifica intenção e não concede autoridade.

Não cria memória vetorial, embeddings, sincronização externa, busca semântica, captura automática de conversa, browser, n8n, MCP tool execution, documentos locais ou autorização por conteúdo lembrado.

## Domínio, canal, autonomia e capacidade

- Domínio: contexto local de projeto e contexto pessoal básico.
- Canal: CLI, Gateway API protegida e Workbench local.
- Autonomia: somente lembrar/mostrar/esquecer notas explícitas, dentro de escopo local.
- Capacidade: JSONL local escopado, com limites de tamanho, projeto e tipo.

## Mudança funcional

`memory-context` aceita `show`, `remember` e `forget`. Contextos `project` e `personal` ficam separados por diretório e `project_id` validado. `remember` é escrita explícita; `forget` adiciona tombstone e não reescreve o histórico. `show` é read-only.

O Gateway expõe `/v1/gateway/memory-context`; a UI adiciona um painel de Memória local. A CLI ganha `lai-gateway memory-context` para teste operacional controlado.

## Segurança preservada

- Memória não concede autoridade, aprovação, capability ou permissão.
- Conteúdo lembrado é dado não confiável.
- Conteúdo com formato de segredo é rejeitado antes da persistência.
- Caminhos ficam dentro do escopo LAI; traversal e symlink são bloqueados.
- Sem rede, shell, tools, servidor, download, modelo, browser, n8n, social/career ou documentos.

## Evidência

Testes cobrem isolamento por projeto, separação pessoal/projeto, bloqueio de segredos, tombstone, CLI, API/UI e documentação canônica.

Gate local: `PYTHON=python3 make check`.
