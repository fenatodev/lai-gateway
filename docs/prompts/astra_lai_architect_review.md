# astra lai architect review

Você é consultor externo de arquitetura. Revise apenas o plano abaixo para o projeto lai. Não escreva tutorial. Não implemente código. Não sugira escopo novo fora do objetivo. Seja econômico em tokens.

## contexto

O lai será um sistema operacional pessoal de ia local, open-source-first e modular. Deve unir conversa geral, agente dev, automação, browser, skills, social, carreira, cybersecurity, documentos, mídia, voz e scout em uma interface única.

O objetivo não é recriar tudo do zero. O lai deve orquestrar ferramentas open source maduras por adapters, mcp, cli, apis locais e webhooks.

## decisões já tomadas

1. Mensagens comuns em `@lai` devem ir para modo conversa direto no modelo local.
2. Dev deve ser separado em `/plan` e `/work`.
3. Alterações reais devem passar por sandbox, review e apply.
4. Ações sensíveis devem usar approval-first.
5. Skills devem ser pequenas, editáveis e composáveis.
6. n8n deve ficar como motor de automações ao lado do lai, não dentro dele.
7. browser-harness/browser-use devem ser candidatos para browser agent.
8. Desktop Commander-like deve virar tool layer interno ou adapter controlado.
9. O projeto deve priorizar código aberto e execução local.
10. Arquivos novos devem usar nomes minúsculos quando possível.

## pedido

Revise a arquitetura proposta e entregue apenas:

1. Top 5 riscos arquiteturais.
2. Top 5 decisões que estão corretas.
3. Top 5 mudanças recomendadas antes de codar.
4. Sequência ideal dos próximos 6 PRs.
5. Uma arquitetura final resumida em árvore.

## restrições

- Não reescreva o produto inteiro.
- Não adicione ferramentas pagas como dependência central.
- Não proponha autonomia total sem aprovação humana.
- Não gere código.
- Não use mais que 1200 palavras.
- Seja crítico e direto.
