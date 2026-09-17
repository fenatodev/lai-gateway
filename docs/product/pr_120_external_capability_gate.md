# PR120 — Gate de primeira capacidade externa candidata

## Escopo

Adicionar `external-capability-gate/v1` para escolher e avaliar uma primeira capacidade externa candidata sem habilitar execução externa ampla.

A candidata selecionada nesta etapa é `browser.public_source_inspection`, derivada do `public-browser-inspector/v1`: uma URL pública explícita por solicitação, source inspector restrito e links públicos como strings inertes. O gate apenas decide se essa candidata é aceitável como próximo caminho read-only; ele não executa a capacidade nem amplia autoridade.

## Contrato

- Domínio: governança de capacidade externa.
- Canal: CLI, API protegida do Gateway e Workbench.
- Autonomia: avaliação read-only de uma candidata explícita.
- Capacidade: `external_capability.go_no_go_candidate`.
- Executor: nenhum executor novo; o gate só consulta evidência local e o baseline `external-expansion-gate/v1`.
- Dados tocados: documentação local, testes locais e plano read-only do browser público.
- Efeito externo: nenhum; o gate não faz GET, não segue links e não chama serviços.
- Autorização: nenhuma autorização efetiva é criada.

## Entrega

- Comando `lai-gateway external-capability-gate` com `--candidate`.
- Endpoint protegido `/v1/gateway/external-capability-gate`.
- Painel “Capacidade candidata” no Workbench.
- Catálogo explícito de candidatas: source inspector público, browser autenticado, n8n real, MCP amplo e envio externo.
- Decisão `go_for_limited_public_read_only_candidate` somente para `browser.public_source_inspection` quando a evidência local estiver completa.
- Decisão `no_go_for_selected_candidate` para browser autenticado, n8n real, MCP amplo, mensagens externas ou candidata desconhecida.

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
- Não executa workflow n8n.
- Não chama MCP amplo.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não chama Harness.
- Não executa tools.
- Não realiza efeito externo.

## Critério de aceitação

`make check` deve passar. README, matriz, índice e prontidão alpha devem declarar `external-capability-gate/v1` sem apresentar o gate como browser autenticado, automação n8n real, MCP amplo, mensagem governada pronta, publicação ou executor externo.
