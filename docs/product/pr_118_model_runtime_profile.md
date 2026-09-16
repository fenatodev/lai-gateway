# PR118 — model runtime profile UX

## Objetivo

Adicionar `model-runtime-profile/v1` para tornar visível o estado operacional do modelo local sem gerenciar runtime automaticamente.

## Entrega

- Módulo `lai_gateway/model_runtime_profile.py`.
- CLI `lai-gateway model-runtime-profile`.
- API protegida `/v1/gateway/model-runtime-profile`.
- Botão e saída no Workbench para perfil do runtime.
- Testes unitários, API/UI e documentação de produto.

## Restrições

- Não baixa modelo.
- Não inicia runtime.
- Não inicia servidor.
- Não chama endpoint público.
- Não roda probe local automaticamente.
- Não usa cloud fallback.
- Não imprime token ou chave.
- Não escreve arquivo.
- Não executa tool.
- Não chama Harness.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não habilita browser autenticado.
- Não ativa n8n real.
- Não chama MCP amplo.
- Não usa credenciais para ação externa.
- Não envia mensagem.
- Não publica.
- Não realiza efeito externo.

## Critérios de aceitação

- Perfil distingue configuração, prontidão, fallback e necessidade de probe.
- Saída é secret-free e não expõe valor de chave.
- API privada exige autenticação quando `private_bind_enabled` está ativo.
- Workbench mostra perfil sem iniciar runtime ou executar diagnóstico de rede.
- `make check` verde.
