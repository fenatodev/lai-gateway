# LAI local clean dogfood

Checklist operacional do PR103 para validar o alpha técnico em um checkout limpo. Este documento complementa `docs/product/post_pr100_roadmap.md` e não substitui `release-check`, `alpha-readiness` ou revisão humana.

## Escopo

O dogfood local cobre somente:

- versão e árvore Git do checkout;
- gates `release-check` e `alpha-readiness`;
- superfície do Workbench já presente nos assets locais;
- modelo local ausente com fallback explícito;
- modelo local presente por fixture efêmera em loopback;
- `document-text-local/v1` e `document-workbench/v1` com `.txt/.md/.json` restritos.

## Comando

```bash
PYTHON=python3 scripts/local-clean-dogfood.sh
```

Para testar o plano sem executar o loop:

```bash
scripts/local-clean-dogfood.sh --check-only
```

Durante desenvolvimento de PR, `--allow-dirty` permite rodar o loop em árvore suja, mas o uso normativo pós-release deve ser em checkout limpo. Por padrão o script usa a versão declarada do pacote; `LAI_GATEWAY_DOGFOOD_TARGET` só deve ser usado para reprodução controlada.

## Garantias negativas

O script não instala pacotes, não inicia serviço persistente, não usa credenciais, não abre browser, não ativa n8n, não executa tools MCP, não envia mensagens, não publica release, não baixa modelos e não varre HOME. Os únicos arquivos temporários são criados sob `state/` e removidos ao final.

## Interpretação

Resultado `local-clean-dogfood: ready` prova apenas que o checkout consegue percorrer o fluxo técnico local mínimo. Não prova produto completo, agente browser, automação externa, processamento amplo de documentos ou autorização geral.
