# PR 64 — skills registry mínimo

## objetivo

Adicionar um registry local e read-only de skills do LAI sem conceder permissões por skill.

## escopo

- Registrar skills pequenas, composáveis e editáveis como metadados.
- Separar domínio, canal, autonomia e capacidade em cada skill.
- Expor inspeção via CLI e endpoint do gateway.
- Garantir que nenhuma skill conceda permissão ou execute adapter.

## fora de escopo

- Não executar skills.
- Não criar plugin loader.
- Não integrar MCP, browser, n8n ou voice.
- Não criar memória persistente de skills.
- Não elevar permissões por canal ou skill.

## contrato

Skill descreve intenção operacional e composição. Permissão continua sendo decisão do permission engine/tool layer. `grants_permissions` deve permanecer falso para todas as skills registradas.
