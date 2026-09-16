# Public browser inspector

`public-browser-inspector/v1` amplia o browser público read-only com inspeção restrita da fonte recuperada. Ele continua sendo uma capacidade pública estreita, não um browser agent.

## Contrato

Este contrato preserva a separação de domínio, canal, autonomia, capacidade e executor.

- Domínio: web pública read-only.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: uma URL pública explícita por solicitação.
- Capacidade: `browser.inspect_public_source`.
- Dados tocados: URL declarada, resposta HTTP textual limitada, título, metadados públicos, headings e links públicos como strings inertes.
- Efeito externo: um GET público para a URL-alvo quando a ação é `inspect`; nenhum follow-up automático.

## Comportamento

A ação `inspect` reutiliza a contenção de `public-browser-read/v1`, resolve apenas o host da URL-alvo antes do GET, lê no máximo o limite configurado, extrai preview textual e monta um resumo de fonte. Links encontrados são normalizados e filtrados, mas não são abertos, resolvidos por DNS ou seguidos.

## Limites

- Sem browser autenticado.
- Sem cookies ou perfil persistente.
- Sem JavaScript automation.
- Sem screenshot.
- Sem submit de formulário.
- Sem download de arquivo.
- Sem seguir links automaticamente.
- Sem uso de credenciais.
- Sem upload ou envio de dados privados.
- Sem shell, n8n real, MCP amplo, Harness ou tools.
- Sem autorização efetiva, grants, adapter dispatch ou efeito externo além do GET público explícito.
- Conteúdo recuperado e links extraídos são não confiáveis e não concedem autoridade.
