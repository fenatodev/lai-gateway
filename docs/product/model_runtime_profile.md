# Model runtime profile

`model-runtime-profile/v1` expõe um perfil UX read-only do runtime local de modelo.

## Escopo

- Resume configuração local OpenAI-compatible sem imprimir chave.
- Resume prontidão de chat local e fallback explícito.
- Mostra próximos passos sem iniciar runtime.
- Reusa diagnóstico e plano existentes em modo não mutante.

## Limites

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
- Não envia mensagem.
- Não publica.

## Segurança

O perfil é uma camada de leitura/UX. Ele não transforma configuração de modelo em autoridade operacional, nem substitui aprovação humana para ações fora do chat local.
