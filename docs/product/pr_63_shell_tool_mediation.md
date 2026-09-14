# PR 63 — shell e tool mediation

## objetivo

Conter uso de shell/processos no `lai-gateway` para que comandos locais reais passem por um mediador explícito antes da execução.

## escopo

- Criar um mediador interno para `subprocess.run` e `subprocess.Popen`.
- Exigir capability nomeada para processos locais.
- Bloquear comando string e capability desconhecida.
- Migrar chamadas reais de subprocess em módulos de produção para o mediador.
- Adicionar teste estático impedindo bypass por `subprocess.run`/`subprocess.Popen` fora do mediador.

## fora de escopo

- Não criar sandbox novo.
- Não executar MCP tools.
- Não ampliar permissões.
- Não alterar comportamento de browser, n8n, voz ou adapters futuros.
- Não trocar harness por shell local.

## contrato

O gateway pode iniciar processos internos conhecidos somente quando a capability estiver declarada no mediador. Shell genérico continua proibido. O mediador não concede permissão; ele apenas força uma passagem única e testável para execução local.
