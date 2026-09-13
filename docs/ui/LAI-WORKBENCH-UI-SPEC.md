# LAI Workbench — especificação de UI

Status: proposta de arquitetura, sem implementação. Data: 2026-09-12.

## 1. Visão geral

Agent Workbench minimalista: projeto visível, chat central e review contextual. Operar capacidades existentes sem terminal, IDs digitados ou cópia de hashes. Harness executa autoridade local; Gateway apresenta e encaminha intenções pelas APIs seguras existentes.

## 2. Problema da UI atual

`lai_gateway/static/index.html` reúne painéis operacionais, campos técnicos e muitos botões. O workbench exige modo técnico, run ID, SHA e polling manual, expondo resultados JSON. `app.js` já integra contrato, projetos, runs, eventos, review, promotion e cancelamento. O redesenho reorganiza essa base; não requer outro backend.

## 3. Princípios de design

- Chat limpo como referência conceitual do ChatGPT; sidebar simples como VS Code/Cursor; review por arquivo como GitHub PR.
- Progressive disclosure: tarefa primeiro, detalhes técnicos sob demanda.
- Uma ação primária por contexto; estado e permissões confirmados pelo Harness.
- Teclado, foco previsível, rótulos claros e estados sem depender apenas de cor.

## 4. Layout proposto em texto/ASCII

```text
+---------------------------------------------------------+
| Projeto / branch                         Conexão   [...] |
+-------------+---------------------------+---------------+
| Projetos    | Observar | Trabalhar      | Review        |
| Sessões     |          | Aplicar        | (contextual)  |
| Runs        |                           | Arquivos      |
| recentes    | Conversa e resultado      | Validação     |
|             | Estado do run             | Telemetria    |
| Nova        |                           | Diff          |
| conversa    | Mensagem...      [Enviar] | Ação adequada |
+-------------+---------------------------+---------------+
| Avançado / Debug — recolhido                             |
+---------------------------------------------------------+
```

Sem alterações, review fica fechado. Em telas estreitas, sidebar vira gaveta e review ocupa aba; layout responsivo não concede trabalho remoto.

## 5. Componentes principais

| Componente | Responsabilidade |
| --- | --- |
| Cabeçalho/sidebar | Projeto e branch; somente workspaces registrados. Sessões/runs por título e estado, sem paths/IDs digitados. |
| Chat | Mensagens, resultado e cartão do run. Reutilizar sessões suportadas, sem prometer memória entre runs não vinculados. |
| Seletor | Três opções abaixo; subtipos técnicos sob demanda, sem nova inferência para escolher modo. Selecionar não executa. |
| Review | Arquivos relativos, validação, duração/chamadas/tokens disponíveis e diff somente leitura. Dado ausente aparece como indisponível. |

| Opção | Mapeamento |
| --- | --- |
| **Observar** | `diagnose` por padrão; `plan`, `review`, `security`, `release` sob demanda. Sem escrita no projeto. |
| **Trabalhar** | `implement` por padrão; `fix`, `refactor`, `ci-fix` sob demanda. Trabalho isolado autorizado. |
| **Aplicar** | Review/promotion do run existente, não novo modo de execução. Indisponível sem proposta elegível. |

Ações: **Ver diff**, **Aplicar alteração**, **Descartar**, conforme contexto. Descartar abandona a proposta na UI e preserva histórico; não apaga sandbox nem desfaz promoção. Não existe API de descarte nesse contrato.

## 6. Estados da interface

| Estado | Evidência/comportamento |
| --- | --- |
| preparando | Criação/fila/preflight confirmado; bloquear envio duplicado. |
| executando | Run ativo; acompanhamento automático e Cancelar. |
| validando | Fase explicitamente informada; não inferir pelo tempo decorrido. |
| pronto para revisão | Alteração revisável disponível; destacar review. Aplicar depende dos gates. |
| erro | Falha informada, inclusive validação reprovada; causa segura e próxima ação. |
| timeout | Prazo excedido confirmado pelo backend; não confundir com falha de polling. |

Auxiliares: ocioso, concluído sem alteração, cancelando, cancelado, aplicado e conexão interrompida. Read-only concluído não abre review vazio. Aplicado exige confirmação do Harness.

## 7. Fluxo principal do usuário

1. Carregar contrato/projeto registrado; Observar é padrão. Informar capability indisponível sem JSON.
2. Usuário conversa, escolhe Observar/Trabalhar e envia. UI mantém workspace, sessão, modelo configurado e run internamente.
3. Acompanhar eventos por cursor e apresentar estado/resumo, sem polling manual obrigatório.
4. Havendo alteração, destacar review com arquivos, validação, telemetria e diff por arquivo. Truncamento relevante impede revisão completa e bloqueia Aplicar.
5. Vincular review a workspace/run/SHA recebido; confirmar **Aplicar alteração** com resumo e destino, sem copiar hash manualmente.
6. Harness revalida hash, baseline e gates. Drift exige nova revisão, nunca troca silenciosa do SHA aprovado. Mostrar destino real da promoção, sem prometer commit, push, merge ou escrita direta no checkout.

## 8. Fluxo de erro/timeout/cancelamento

Erro mostra mensagem curta e próxima ação contextual. Desconexão oferece reconectar/consultar o run existente, sem reenviar trabalho. Parar polling não cancela.

Cancelar usa lifecycle existente; manter cancelando até confirmação. Timeout/falha durante promotion pode deixar resultado desconhecido: consultar estado, sem retry automático ou sucesso presumido. Trocar projeto/run invalida review/hash selecionado, sem cancelar silenciosamente a execução.

## 9. O que fica oculto em Avançado/Debug

Run ID, patch SHA, JSON diagnóstico em formato bruto **já sanitizado**, eventos, telemetria completa disponível, modelo/configuração, contrato e logs permitidos. Saúde/MCP/integrações ficam nessa área ou navegação secundária.

Tudo recolhido por padrão. Debug/copiar nunca inclui tokens de controle/CSRF, segredos, paths privados ou conteúdo sensível. Não expor dados que o contrato não disponibiliza com segurança.

## 10. Limites de segurança que a UI não pode violar

- Preservar loopback para local-chat/work/review/promotion. Acesso privado/remoto mantém apenas o caminho read-only autorizado.
- Preservar verificações server-side de cliente, Host, Origin, auth, CSRF e capabilities; botão oculto não é enforcement.
- Tokens Harness ficam server-side, sem browser storage. Escapar chat/diff/logs; somente paths relativos autorizados.
- Manter sandbox, validação, review explícito e hash vinculado. SHA válido isoladamente não autoriza promotion.
- Não adicionar shell, MCP executável, Git remoto, paths arbitrários ou autoridade ao Gateway.

## 11. Plano futuro em no máximo 3 PRs pequenos

| PR futuro | Corte e verificação |
| --- | --- |
| 1 — Estrutura | Sidebar/cabeçalho/chat e Debug recolhido; verificar teclado, layout e restrição remota, preservando APIs. |
| 2 — Execução | Observar/Trabalhar, identificadores internos, eventos/estados; verificar envio único, troca de contexto, reconnect, timeout e cancelamento. |
| 3 — Review | Diff/validação/telemetria, Aplicar vinculado ao hash e descarte visual; verificar drift, truncamento, resultado incerto e negação remota. |

Implementação posterior. Capability ausente fica indisponível; não criar backend nem afrouxar gates para fechar PR de UI.

## 12. Critérios de aceite objetivos

- Primeiro acesso mostra projeto, três opções e chat; sem terminal, JSON ou campos de ID/SHA. Debug e review vazio recolhidos.
- Observar e Trabalhar→review→promotion funcionam sem terminal ou cópia de identificadores.
- Uma ação primária destacada por contexto; controles inválidos indisponíveis com motivo.
- Fixtures distinguem sucesso, validação reprovada, timeout, cancelamento e desconexão; dados ausentes não viram sucesso.
- Review contém arquivos, validação, telemetria e diff; hash/drift/incompatibilidade/truncamento relevante bloqueiam Aplicar.
- Selecionar Aplicar não executa; confirmação usa proposta revisada. Descartar não envia mutação nem promete limpeza/rollback.
- Reconexão/clique repetido não reenviam trabalho ou promotion; troca de workspace/run não reutiliza SHA.
- Fixtures remotas não executam work/promotion; segredos/paths sensíveis não aparecem nem em Debug/copiar.
- Teclado e tela estreita preservam contexto e ações.

## 13. Fora de escopo

Implementação nesta entrega; editor completo, terminal padrão, desktop nativo, novos endpoints/permissões, novos níveis de autonomia, modelo/router novo, mudanças no Harness/sandbox/promotion, descarte físico, rollback automático, branch/commit/PR/release ou alterações em outros arquivos.
