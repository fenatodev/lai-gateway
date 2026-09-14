# pr 62 conversation first routing

## objetivo

Fazer o chat `@lai` responder mensagens comuns como conversa direta, sem criar run no harness.

## problema

Antes deste PR, qualquer mensagem comum com texto no participante do VS Code criava um run read-only `mode=plan` no harness. Isso misturava conversa comum com dev assistido.

## escopo

- Mensagem comum `@lai texto` deve chamar conversa direta pelo modelo local via gateway.
- `/plan texto` deve ser o caminho explícito para criar run read-only no harness.
- `/health`, `/workbench` e `/pasta` mantêm o comportamento atual.
- O gateway deve expor uma rota de conversa local sem criar run e sem executar ferramentas.

## fora de escopo

- Não implementar agente dev completo.
- Não implementar `/work`.
- Não adicionar browser, n8n, voz ou adapters novos.
- Não publicar, aplicar patch remoto, usar sudo ou instalar dependências.

## condição de aceite

- Teste cobrindo mensagem comum sem harness.
- Teste cobrindo `/plan` explícito criando run read-only.
- Rota de conversa local não inicia servidor, não modifica arquivos e não baixa modelo.
- Prompt do usuário não é ecoado em payloads de diagnóstico/teste.
- Suite de testes passa.
