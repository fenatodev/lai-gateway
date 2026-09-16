# LAI alpha readiness

Critérios pós-PR90 para alpha público técnico no PR100. [Índice](index.md), [roadmap](roadmap.md) e [matriz](implementation_matrix.md).

## Promessa pública permitida

Workbench local-first experimental para conversa e dev assistido via Harness, com fundação de governança e um adapter local mínimo. Alpha público não significa produto completo nem autorização para capacidades externas.

Não declarar browser agent completo, automação n8n real, voz operacional, MCP tool execution generalizado, automação social/carreira com envio real, processamento completo de documentos/mídia ou instalação one-click universal.

## Limitações conhecidas

- Effective authorization está restrita a adapter-dry-run; não concede capability ampla e não persiste aprovação.
- local_status executa código in-process restrito; não prova o ciclo geral de autorização non-dry-run.
- Identidade usuário/cliente/agente/serviço precisa de vínculo testado, além de campos declarativos.
- Persistência, expiração, revogação, consumo único, restart recovery e bloqueio contra duplicação de efeito ainda precisam de prova integrada nessa cadeia.
- Audit log sanitizado não equivale a execução autorizada, integridade inviolável ou recuperação transacional.
- Read-only declarado ou simulado não é read-only efetivamente imposto; afirmar contenção apenas com evidência específica.
- Dev/Workbench depende de Harness compatível; modelo local depende de runtime configurado. Interface existente não prova primeira execução reproduzível.
- Browser/n8n/MCP/voz/social permanecem contratos ou planos; documentos locais entram apenas no escopo restrito PR98–99.
- Telegram outbound já realiza envio operacional opt-in. Requer ação explícita do operador e destino configurado; não possui a cadeia geral durável de aprovação por mensagem. Novos fluxos exigem aprovação explícita de conteúdo/destino e não podem usar enable-send como consentimento permanente.
- Quickstart, empacotamento mínimo, guia visual e versão alpha ainda precisam de consolidação e evidência.

## Go para alpha público técnico

Todos os itens são obrigatórios; esta lista não afirma que já passaram:

- Quickstart reproduzível por usuário novo, instalação limpa em ambiente suportado e diagnóstico de Harness/token/modelo ausentes (PR91).
- Empacotamento mínimo identificado, versionamento inequívoco, artefato correspondente ao commit e release checklist com guia visual sanitizado (PR92).
- Identidade testável (PR93), uma ação local autorizada non-dry-run (PR94) e persistência/restart/recovery com expiração, revogação, consumo único e antirreplay (PR95).
- Primeira conversa local, health/fallback explícitos, contexto isolado e documentos locais restritos demonstrados nos escopos PR96–99.
- `python3 -m unittest tests.test_product_docs -v`, `PYTHON=python3 make check` e `git diff --check` verdes; CI e publication scan conferidos para o commit candidato, sem inferir verde histórico.
- README, matriz e UI com ausência de overclaiming; limitações conhecidas visíveis, sem segredos ou dados privados nas evidências.
- Capacidades externas bloqueadas conforme roadmap; aprovação humana separada para publicação do alpha.

## No-go

Qualquer critério sem evidência impede o go. Em especial: instalação não reproduzível, versão ambígua, falha de validação, identidade autodeclarada tratada como autoridade, aprovação reutilizada após reinício, duplicação de efeito, adapter sensível sem gate, shell genérico no caminho de adapter ou promessa de contrato como funcionalidade pronta.

## Decisão atual

No-go para declarar prontidão pública apenas com a consolidação documental PR90. PR91–99 devem fornecer as evidências, avaliadas no PR100. Ainda não está apto a ser chamado de produto completo. Não há bump, tag, publicação ou mudança funcional neste PR.

## Restrições públicas

Browser, n8n, voz, execução real de tools MCP, social e automações externas governadas não estão disponíveis como funcionalidades prontas. Contratos e simulações não autorizam execução real.

local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.

Telegram outbound tem limite conhecido: não possui aprovação durável por mensagem.
