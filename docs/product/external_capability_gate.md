# External capability gate

`external-capability-gate/v1` é um gate read-only para selecionar e avaliar uma capacidade externa candidata.

## Contrato

- Domínio: governança de capacidade externa.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: uma candidata explícita por avaliação.
- Capacidade: `external_capability.go_no_go_candidate`.
- Dados tocados: documentação, testes e evidência runtime local estreita.
- Efeito externo: nenhum durante o gate.

## Candidata selecionada

A primeira candidata aceita pelo gate é `browser.public_source_inspection`, limitada ao caminho público read-only já contido em `public-browser-inspector/v1`. O gate pode retornar go para essa candidata como caminho read-only limitado, mas não habilita uma nova execução e não concede autoridade durável.

## Candidatas bloqueadas

Browser autenticado, n8n real, MCP amplo e mensagens externas permanecem no-go até terem executor específico, política, aprovação humana, grants single-use quando aplicável e testes negativos próprios.

## Limites

- Sem browser autenticado, cookies ou perfil persistente.
- Sem JavaScript automation, formulário, download ou link-following.
- Sem uso de credenciais.
- Sem n8n real, workflow, webhook ou activation.
- Sem MCP amplo, broker externo ou tool execution.
- Sem mensagens, publicação, candidatura, formulário ou compra.
- Sem autorização efetiva, grants, adapter dispatch, Harness ou tools.
- Conteúdo recuperado, documentação e testes não concedem autoridade.
