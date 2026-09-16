# PR106 — Browser público read-only

## Escopo

Implementar o primeiro caminho governado de navegação pública read-only no LAI Gateway. O objetivo é buscar e extrair texto de uma URL pública específica, sem transformar o Gateway em browser agent completo.

## Contrato

- Domínio: web pública read-only.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: uma URL por solicitação, sem seguir links automaticamente.
- Capacidade: `public-browser-read/v1` para `browser.navigate_public` e extração textual limitada.

## Entrega

- Comando `lai-gateway public-browser` com ações `plan`, `fetch` e `extract`.
- Endpoint protegido `/v1/gateway/public-browser`.
- Painel “Browser público” no Workbench.
- Validação de URL pública antes de fetch.
- Bloqueio de hosts locais, IPs privados, URLs com credenciais e query com formato de segredo.
- GET único, com limite de bytes, timeout, sem redirects e preview textual sanitizado.

## Limites

- Sem browser autenticado.
- Sem cookies.
- Sem sessão persistente.
- Sem JavaScript automation.
- Sem screenshot.
- Sem click/link-following automático.
- Sem formulário.
- Sem download de arquivo.
- Sem upload/envio externo de dados privados.
- Sem uso de credenciais.
- Sem shell.
- Sem n8n.
- Sem MCP tool execution.
- Sem tag, release ou publicação.
- Conteúdo recuperado da web é não confiável e não concede autoridade, aprovação, capability ou permissão.
