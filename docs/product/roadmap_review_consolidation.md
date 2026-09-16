# Consolidação das revisões do roadmap — PR90

## Origem e autoridade

Consolidação pós-PR89 dos pontos atribuídos a GPT-6/Astra e Claude fornecidos pelo mantenedor na solicitação do PR90, confrontados com os documentos e código locais. Não foram fornecidas transcrições completas separadas de cada parecer; não se atribui uma conclusão específica a um revisor sem essa evidência. As revisões históricas [Astra](astra_architecture_review.md) e [Codex/Astra](codex_astra_architecture_review.md) são contexto adicional.

GPT-6/Astra, Claude e Codex são revisores, não autoridade automática. Parecer externo é insumo crítico; não prova segurança, testes verdes ou autorização. A adoção passa por decisão humana versionada. Este PR altera documentação e testes documentais, não comportamento.

## Pontos aceitos e mudanças

| Insumo aceito | Mudança documental / marco |
| --- | --- |
| 1. Risco de overclaiming em browser, MCP, autorização, auditoria e adapters | Matriz separa maturidade, disponibilidade e limite; README reduz promessa |
| 2. Effective authorization estreita em adapter-dry-run | Matriz/readiness explicitam escopo, ausência de persistência e distinção de local_status |
| 3. Falta gate real não-dry-run | PR94 antes de browser/n8n/MCP/social reais |
| 4. Falta prova de persistência, expiração, revogação, consumo único e restart recovery | PR95 testa reinício, replay, concorrência e duplicação de efeito; resultado desconhecido não autoriza retry |
| 5. Identidade usuário/cliente/agente/serviço precisa ser testável | Linha explícita na matriz e PR93 com rejeição de falsificação |
| 6. Telegram outbound requer limites e aprovação explícita | Distinguir operação opt-in existente de novos envios governados; habilitar envio não é aprovação durável por mensagem |
| 7. Read-only ambíguo | Distinguir declarado, simulado e efetivamente imposto com testes negativos |
| 8. Instalação e promessa pública devem anteceder alpha | README no PR90; quickstart/empacotamento mínimo PR91, checklist/guia visual PR92, alpha PR100 |
| 9. Docs antigos não podem orientar a fila atual | Índice classifica histórico, contratos normativos e documentos atuais; avisos nas revisões antigas |
| 10. Revisores não decidem autoridade | Roadmap e índice registram necessidade de evidência e revisão humana |

## Constatações locais relevantes

`effective_authorization.py` só aceita adapter-dry-run e informa authorization_persisted=false. `adapter_dispatcher.py` tem caminho próprio para local_status baseado em allowlist, decisão allow e dispatch explícito; não exige a autorização efetiva geral. A confirmação no Workbench não transforma isso em aprovação durável no backend. Portanto, o título histórico do PR88 não deve ser lido como prova de uma cadeia geral approve → execute.

`telegram.py` possui envio real mediante enable-send e configuração. Não é correto dizer que nenhum envio existe; também não é correto apresentá-lo como automação governada pronta. Os bloqueios do roadmap se aplicam à expansão dos agentes/adapters, sem alegar bloqueio novo no CLI legado.

## Rejeitados ou adiados

Nenhuma das dez críticas foi rejeitada. Foram adiadas a execução externa e qualquer implementação dos gates: dependem dos próximos PRs e de specs próprias. Não adotar como conclusão que simulação, log persistido ou handler in-process provam autorização real completa. Não reescrever o produto, mover histórico, alterar Harness ou trocar modelo nesta consolidação.

A fila anterior PR90–107 foi substituída pela sequência PR90–100 no roadmap, preservada no histórico Git. Browser/n8n/MCP/social reais ficam sem data/PR prometido até os gates. Publicação depende do go/no-go; alpha técnico não significa produto completo.
