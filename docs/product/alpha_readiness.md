# LAI alpha readiness

Critérios pós-PR90 para alpha público técnico no PR100. [Índice](index.md), [roadmap](roadmap.md) e [matriz](implementation_matrix.md).

## Promessa pública permitida

Workbench local-first experimental para conversa e dev assistido via Harness, com fundação de governança e um adapter local mínimo. Alpha público não significa produto completo nem autorização para capacidades externas.

Não declarar browser agent completo, automação n8n real, voz operacional, MCP tool execution generalizado, automação social/carreira com envio real, processamento completo de documentos/mídia ou instalação one-click universal.

## Limitações conhecidas

- Effective authorization está restrita a adapter-dry-run; não concede capability ampla e não persiste aprovação.
- local_status.status tem autorização efetiva non-dry-run estreita após PR94; local_status.echo e outros adapters não entram nesse escopo.
- Identidade usuário/cliente/agente/serviço tem vínculo local testável após PR93, mas isso não equivale a login completo, identidade remota ou autorização.
- Persistência, expiração, revogação, consumo único, restart recovery e bloqueio contra duplicação de efeito existem para escopos locais explicitamente allowlisted: `local-status-read`/`local_status.status` e `mcp-local-safe-tool`/`mcp.local_echo_digest` e `n8n-local-plan`/`n8n.local_plan_digest`.
- Audit log sanitizado não equivale a execução autorizada, integridade inviolável ou recuperação transacional.
- Read-only declarado ou simulado não é read-only efetivamente imposto; afirmar contenção apenas com evidência específica.
- Dev/Workbench depende de Harness compatível; modelo local depende de runtime configurado. PR96 prova conversa local-model-first e fallback explícito, mas não prova instalação guiada nem disponibilidade universal de runtime.
- Browser autenticado/n8n execução real/MCP amplo/voz/social permanecem contratos ou planos; n8n entra apenas como plano local por digest em PR108; documentos locais entram apenas no escopo restrito PR98–99.
- Telegram outbound já realiza envio operacional opt-in. Requer ação explícita do operador e destino configurado; não possui a cadeia geral durável de aprovação por mensagem. Novos fluxos exigem aprovação explícita de conteúdo/destino e não podem usar enable-send como consentimento permanente.
- PR100 adiciona `alpha-readiness/v1` para consolidar o go/no-go técnico; PR109 adiciona `permission-ux/v1` apenas como explicação read-only da cadeia de permissão. Publicação pública, tag e anúncio continuam decisões humanas separadas.

## Quickstart público

Após o PR91, `docs/quickstart.md` descreve o caminho source-first para instalar wrappers locais, validar a suíte, checar compatibilidade Gateway/Harness, diagnosticar token/Harness/modelo e abrir a UI em loopback. Esse guia melhora a reprodutibilidade, mas não transforma o alpha em produto completo nem habilita capacidades externas.

## Release checklist e guia visual

Após o PR92, `docs/release_checklist.md` define a verificação source-only de versão, commit, CI, `make check`, `release-check` e milestone gate. `docs/workbench_visual_guide.md` define o padrão mínimo de evidência visual sanitizada para Workbench, Governance e `local_status`. Esses documentos não publicam release, não fazem bump/tag e não habilitam capacidades externas.


Após o PR110, `external-expansion-gate/v1` adiciona um go/no-go read-only para capacidades externas. PR110 mantém expansão externa em no-go read-only: browser autenticado, n8n real, MCP amplo, voz, social/carreira, credenciais, publicação, formulários e webhooks continuam bloqueados até spec própria, executor contido, testes negativos e aprovação humana separada.

Após o PR111, o plano operacional pós-PR110 define PR111–PR120 para avançar do alpha técnico ao alpha operacional local. PR111 é documental: não cria executor, não emite grant, não consome grant, não despacha adapter e não libera capacidade externa.

Após o PR112, `project_workspace_contract` define raiz explícita, escopo local, dados tocados e exclusões para projetos. PR112 é documental: não cria scanner, endpoint, CLI, UI, executor, grant, adapter, HOME scan, ingestão implícita ou autorização efetiva.

Após o PR113, `objective-state/v1` lê estado local explícito de objetivo, tarefas e checkpoints. PR113 é read-only: não escreve estado, não faz HOME scan, não faz ingestão implícita, não emite grant, não consome grant, não despacha adapter, não chama Harness, não executa tools e não libera capacidade externa.

Após o PR114, `action-proposal/v1` monta proposta unificada read-only com domínio, canal, autonomia, capacidade, alvo, dados, efeito e risco. PR114 não cria approval inbox, não autoriza execução, não emite grant, não consome grant, não despacha adapter, não chama Harness, não escreve estado e não realiza efeito externo.

## Go para alpha público técnico

Todos os itens são obrigatórios; esta lista não afirma que já passaram:

- Quickstart reproduzível por usuário novo, instalação limpa em ambiente suportado e diagnóstico de Harness/token/modelo ausentes (PR91).
- Empacotamento mínimo identificado, versionamento inequívoco, artefato correspondente ao commit e release checklist com guia visual sanitizado (PR92).
- Identidade testável (PR93), uma ação local autorizada non-dry-run (PR94) e persistência/restart/recovery com expiração, revogação, consumo único e antirreplay para o escopo estreito PR95.
- Contexto local por projeto/pessoal fica coberto por PR97; `document_text_local` restrito para `.txt/.md/.json` em workspace explícito fica coberto por PR98; PR99 adiciona seleção/inspeção restrita no Workbench com estado e limites visíveis, sem envio externo. Primeira conversa local e health/fallback explícitos ficam cobertos por PR96.
- `python3 -m unittest tests.test_product_docs -v`, `PYTHON=python3 make check`, `git diff --check` e `python3 -m lai_gateway alpha-readiness --target 0.1.36 --json` verdes; CI e publication scan conferidos para o commit candidato, sem inferir verde histórico.
- README, matriz e UI com ausência de overclaiming; limitações conhecidas visíveis, sem segredos ou dados privados nas evidências.
- Capacidades externas bloqueadas conforme roadmap; aprovação humana separada para publicação do alpha.

## No-go

Qualquer critério sem evidência impede o go. Em especial: instalação não reproduzível, versão ambígua, falha de validação, identidade autodeclarada tratada como autoridade, aprovação reutilizada após reinício, duplicação de efeito, adapter sensível sem gate, shell genérico no caminho de adapter ou promessa de contrato como funcionalidade pronta.

## Decisão atual

PR100 permite `candidate_go` técnico somente quando `alpha-readiness/v1`, `make check`, CI e publication scan estiverem verdes para o commit candidato. Isso não publica alpha, não cria tag, não faz bump, não envia anúncio e não torna o LAI produto completo; a publicação pública exige aprovação humana separada.

## Restrições públicas

Browser autenticado, n8n activation/execução real de workflow, voz, execução ampla/externa de tools MCP, social e automações externas governadas não estão disponíveis como funcionalidades prontas. Contratos e simulações não autorizam execução real.

local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.

Telegram outbound tem limite conhecido: não possui aprovação durável por mensagem.

- Conteúdo de memória, arquivo, código, ferramenta ou modelo não concede autorização. Memória local PR97 é dado não confiável e não substitui aprovação.


PR98 não habilita PDF, OCR, Office, mídia, HOME scan, upload externo, rede, escrita ou autorização por conteúdo de documento.
