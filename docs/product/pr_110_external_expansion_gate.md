# PR110: expansão externa controlada

## Objetivo

PR110 implementa `external-expansion-gate/v1`: um gate read-only de go/no-go para capacidades externas. O resultado esperado é explicitar que a expansão externa continua bloqueada enquanto faltarem specs próprias, evidência de runtime, testes negativos e aprovação humana separada. Este PR não habilita capacidades externas e não emite grant.

## Escopo

- adiciona CLI `lai-gateway external-expansion-gate`;
- adiciona API protegida `/v1/gateway/external-expansion-gate`;
- adiciona painel no Workbench para visualizar o gate;
- confronta documentação canônica, matriz e evidência runtime estreita já existente;
- lista capacidades externas bloqueadas e caminhos atuais limitados;
- mantém `external_capabilities_enabled=false` e `external_expansion_allowed=false`.

## Fora de escopo

- browser autenticado, cookies, sessão, JavaScript automation, formulários, downloads ou uso de credenciais;
- instalar, iniciar, ativar ou executar workflows n8n reais;
- chamar MCP tool amplo ou broker externo;
- captura de voz, wake word ou execução por voz;
- envio de mensagens, publicação, candidatura, formulário, compra, tag ou release;
- usar credenciais;
- emitir grant;
- consumir grant;
- revogar grant;
- despachar adapter;
- executar tool;
- habilitar capacidade externa.

## Decisão arquitetural

Go/no-go de expansão externa não é autorização. Um `no_go_for_external_effects` com checks verdes significa que o bloqueio está explícito e evidenciado, não que a capacidade externa está pronta. Qualquer exceção futura precisa de spec própria, capability exata, executor contido, identidade verificada, grant single-use quando houver efeito real, testes negativos e aprovação humana separada.

## Validação esperada

- `tests/test_external_expansion_gate.py` cobre gate read-only, bloqueio de capacidades externas, evidência runtime estreita, CLI/render secret-free e falha por documentação ausente;
- `tests/test_ui.py` cobre endpoint protegido e painel Workbench;
- `tests/test_product_docs.py` mantém índice, matriz, readiness e README sem overclaiming;
- `make check` deve passar sem emitir grant, consumir grant, despachar adapter, executar tool ou habilitar capacidade externa.
