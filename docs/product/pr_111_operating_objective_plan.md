# PR111 — Plano operacional pós-PR110

## Status

Spec de PR atual. Escopo documental, sem mudança funcional.

## Objetivo

Criar a fonte normativa da próxima fase após o PR110: transformar o alpha técnico do LAI em alpha operacional local, mantendo capacidades externas em no-go até gates próprios.

## Domínio, canal, autonomia e capacidade

```text
domínio: arquitetura / produto / operação local
canal: docs / CLI de validação existente
autonomia: leitura e proposta normativa
capacidade: documentação versionada e testes documentais
```

Este PR não altera executor, adapter, grant, policy runtime, browser, n8n, MCP, Telegram, modelo ou Workbench funcional.

## Entrega

- Novo `docs/product/post_pr110_operating_plan.md`.
- Índice canônico apontando para o plano pós-PR110.
- Matriz de implementação declarando o plano como direção, não capacidade operacional.
- Alpha readiness explicitando que PR111 não libera capacidades externas.
- README apontando o plano operacional como direção pós-PR110.
- Testes documentais para ordem PR111–PR120 e bloqueios de capacidade.

## Fora de escopo

- Habilitar browser autenticado.
- Executar n8n real ou ativar workflow.
- Chamar MCP amplo ou ferramenta externa.
- Usar credenciais.
- Enviar mensagem, publicar, candidatar, submeter formulário ou comprar.
- Alterar fluxo funcional de autorização.
- Criar adapter novo.
- Abrir tag, release ou anúncio.

## Critério de aceite

- Roadmap pós-PR110 existe e declara PR111–PR120 em ordem.
- PR112–PR118 priorizam operação local antes de nova expansão externa.
- PR119 e PR120 preservam bloqueio de browser autenticado, n8n real, MCP amplo, credenciais e efeitos externos.
- Documentos canônicos e README apontam para o novo plano.
- `make check` passa.

## Risco explícito

Este PR não deve ser lido como evidência de capacidade operacional nova. Ele apenas evita que o projeto avance por PRs soltos depois do PR110.
