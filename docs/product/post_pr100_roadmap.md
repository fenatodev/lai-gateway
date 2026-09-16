# LAI post-PR100 roadmap

Roadmap normativo após o PR100. Ele substitui a sequência fechada PR90–PR100 apenas para próximos trabalhos; não altera o estado histórico desses PRs.

## Princípios

- Separar domínio, canal, autonomia e capacidade em todo PR.
- Nenhum canal novo eleva permissão.
- Nenhuma memória, documento, ferramenta, modelo ou conteúdo recuperado concede autorização.
- Capacidades externas continuam bloqueadas até spec própria, executor contido e testes negativos específicos.
- Publicação, tag, release, envio de mensagens, browser autenticado, formulários, candidaturas e credenciais exigem aprovação humana explícita separada.

## Trilhas pós-PR100

| PR | Trilha | Entrega | Gate de saída |
| --- | --- | --- | --- |
| PR101 | Planejamento | Roadmap pós-PR100 | Documento normativo versionado, índice atualizado e testes documentais sem mudança funcional |
| PR102 | Release alpha técnico | Preparação source-first de tag/release | `release-check` e `alpha-readiness` em `main`, nota de release versionada sem overclaiming, aprovação humana antes de tag/publicação |
| PR103 | Dogfood local limpo | Validação ponta a ponta em checkout limpo | `scripts/local-clean-dogfood.sh`, checklist versionado, Workbench, modelo local ausente/presente e documentos restritos |
| PR104 | Onboarding/UX | Redução de fricção inicial | Workbench mostra próximos passos sanitizados para Harness/token/modelo/documento sem vazar segredo |
| PR105 | Modelo local operacional | Runtime local configurável com diagnóstico melhor | Sem download automático, sem nuvem, sem execução de tools e com health/fallback explícito |
| PR106 | Browser público read-only | Implementado como GET público único com extração textual limitada | Sem login, sem cookies, sem formulário, sem download, sem JavaScript automation e com testes negativos próprios |
| PR107 | MCP mínimo governado | Implementado como `mcp.local_echo_digest` local não sensível sob autorização | Capability exata, escopo mínimo, identidade, grant single-use e bloqueio de replay |
| PR108 | n8n mínimo governado | Implementado como plano local por digest | Capability exata, escopo `n8n-local-plan`, identidade, grant single-use; sem instalação, credenciais, webhook, activation ou execução real de workflow |
| PR109 | UX de permissões | Implementado como `permission-ux/v1` read-only | Diferença visível entre intenção, identidade, decisão, registro, aprovação/captura, autorização efetiva, grant e execução; sem emitir/consumir grant ou despachar adapter |
| PR110 | Expansão externa controlada | Go/no-go para capacidades externas | Matriz atualizada, evidência runtime, testes negativos e publicação humana separada |

## Ordem recomendada

Executar PR101 antes de qualquer release ou expansão. Depois, preferir PR102–PR106 para consolidar alpha técnico local e primeira navegação pública restrita antes de PR107+. O risco de pular direto para browser/n8n/MCP é alto: aumenta superfície externa antes de dogfood, UX de falha e diagnóstico de modelo estarem estáveis.

## Fora de escopo até spec própria

- Browser autenticado.
- n8n activation e execução real de workflow.
- MCP tool execution amplo.
- Voz operacional.
- Social/carreira com envio real.
- Formulários, candidaturas, compras ou publicação.
- Uso de credenciais por agente.
- Processamento amplo de PDF/OCR/Office/mídia.

## Critério de mudança

Qualquer PR que altere capacidade funcional sensível deve começar por spec curta e declarar: domínio, canal, autonomia, capacidade, executor, dados tocados, efeito externo, política de autorização, teste positivo e testes negativos. Conteúdo recuperado de arquivos ou memória pode informar a proposta, mas nunca autoriza a execução.
