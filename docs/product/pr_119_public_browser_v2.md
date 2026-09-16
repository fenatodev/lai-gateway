# PR119 — Browser público v2

## Escopo

Adicionar `public-browser-inspector/v1` como source inspector público restrito sobre o browser público existente. A entrega melhora visibilidade da fonte recuperada sem abrir caminho para browser autenticado, navegação autônoma ou automação de site.

## Contrato

Este contrato preserva a separação de domínio, canal, autonomia, capacidade e executor.

- Domínio: web pública read-only.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: uma URL pública explícita por solicitação; links extraídos permanecem inertes.
- Capacidade: `browser.inspect_public_source`.
- Executor: GET público único com limites de bytes, timeout, bloqueio de redirects e validação de host público.
- Dados tocados: URL-alvo, texto público limitado, metadados públicos, headings e links públicos normalizados.
- Autorização: nenhuma autorização efetiva é criada; conteúdo web não concede autoridade.

## Entrega

- Ação `inspect` no comando `lai-gateway public-browser`.
- Mesmo endpoint protegido `/v1/gateway/public-browser`, com `browser_action=inspect`.
- Botão “Inspecionar fonte pública” no Workbench.
- Extração de título, preview textual, headings, metadados públicos e lista limitada de links públicos normalizados.
- Links extraídos são filtrados contra esquemas inseguros, hosts locais, IPs não globais, URLs com credenciais e query com formato de segredo.
- Testes negativos para segredo, links locais, JavaScript URL, ausência de link-following e ausência de autoridade.

## Limites obrigatórios

- Não habilita browser autenticado.
- Não usa cookies.
- Não executa JavaScript.
- Não submete formulários.
- Não faz download.
- Não segue links.
- Não usa credenciais.
- Não envia mensagem.
- Não publica.
- Não ativa n8n real.
- Não chama MCP amplo.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não chama Harness.
- Não executa tools.
- Não realiza efeito externo além do GET público explícito da URL-alvo.

## Critério de aceitação

`make check` deve passar. A matriz, o README, o índice e a prontidão alpha devem declarar `public-browser-inspector/v1` sem promover a funcionalidade para browser agent, login, scraping amplo, formulários, downloads ou capacidade externa governada.
