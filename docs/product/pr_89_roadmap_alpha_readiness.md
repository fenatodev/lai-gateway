# PR 89 — roadmap alignment and alpha readiness

## objetivo

Consolidar a rota pós-PR88 para impedir progresso aparente sem aproximação do objetivo final do LAI.

Este PR não implementa feature nova. Ele cria a fonte única de direção para os próximos incrementos.

## escopo

Incluído:

- roadmap normativo pós-PR88;
- matriz de implementação;
- checklist de prontidão alpha;
- prompt de revisão externa para GPT-6, Codex e Astra;
- atualização da fila antiga para apontar para o roadmap atual.

Fora de escopo:

- browser real;
- n8n real;
- voz real;
- MCP tool execution;
- modelo local novo;
- instalação nova;
- release/tag.

## invariantes

- Cada PR futuro deve apontar para uma linha do roadmap ou da matriz.
- Contrato não pode ser apresentado como implementação.
- GPT-6, Codex e Astra são revisores críticos, não autoridades automáticas.
- O usuário mantém a decisão final de produto.
- Nenhum canal, skill, adapter ou texto eleva permissão.
- Nenhuma capacidade externa deve ser aberta antes de policy, audit e approval gates adequados.

## validação esperada

```text
python3 -m py_compile tests/test_product_docs.py
python3 -m unittest tests.test_product_docs -v
PYTHON=python3 make check
git diff --check
```
