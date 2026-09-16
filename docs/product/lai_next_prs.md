# lai next prs

> Histórico/insumo de revisão. Não define a sequência atual nem comprova capacidade operacional. Consulte o [índice canônico](index.md) e o [roadmap pós-PR90](roadmap.md).

## status pós-PR88

Esta fila é histórica para PR 61-66 e para a transição inicial de adapters. O roadmap normativo atual está em `docs/product/roadmap.md`; a matriz de estado está em `docs/product/implementation_matrix.md`; a prontidão alpha está em `docs/product/alpha_readiness.md`.

Novos PRs devem referenciar o roadmap atual em vez de acrescentar itens livres nesta fila.

## objetivo

Organizar a evolução imediata do LAI após revisões arquiteturais externas.

Esta fila substitui a ordem anterior porque segurança, identidade, lifecycle e roteamento precisam estabilizar antes de novos adapters.

## pr 61: contratos arquiteturais, identidade, autorização e lifecycle

Escopo:

- consolidar responsabilidades do core, adapters, interfaces, skills e plugins;
- separar domínio, canal, autonomia e capacidade;
- definir identidade: usuário, cliente, agente e serviço;
- definir lifecycle único de ação;
- definir semântica de proposta, aprovação, execução, revisão, promoção, apply e publicação;
- registrar que capacidades solicitadas não equivalem a capacidades concedidas.

Condição de aceite:

- documentos em minúsculo atualizados;
- nenhum código funcional alterado;
- fila de PRs revisada;
- termos ambíguos removidos ou definidos.

## pr 62: conversation-first routing

Escopo:

- `@lai mensagem comum` deve responder como conversa direta;
- mensagens comuns não devem criar run no harness;
- `/plan` fica explícito para dev assistido read-only;
- `/workbench` continua abrindo o workbench;
- `/work` fica reservado para dev controlado.

Condição de aceite:

- teste cobrindo mensagem comum sem harness;
- teste cobrindo comando explícito para plano;
- extensão vscode reinstalada se necessário;
- comportamento validado manualmente.

## pr 63: contenção do shell e mediação obrigatória de ferramentas

Escopo:

- tratar filesystem, shell, browser, rede e credenciais como capacidades separadas;
- impedir executor de receber ação negada;
- registrar auditoria mínima;
- revisar perfis que prometem leitura mas permitem shell com efeitos.

Condição de aceite:

- uma ação negada não alcança executor;
- shell local não aparece como leitura segura sem restrição;
- testes simulam tentativa de ultrapassar permissão.

## pr 64: skills registry mínimo

Escopo:

- criar formato mínimo de skill;
- skills declaram entradas, saídas e capacidades solicitadas;
- skills não concedem permissão;
- primeira leva: grill, architect, spec, frontend, dev, security, scout.

Condição de aceite:

- registry carrega skills pequenas;
- composição não amplia privilégio;
- docs explicam como criar uma skill sem alterar core.

## pr 65: dev controlado

Escopo:

- fechar ciclo sandbox, review e apply;
- aprovação deve indicar ação, alvo, conteúdo e validade;
- alteração relevante invalida aprovação;
- repetir ação exige reconciliação quando o resultado anterior for desconhecido.

Condição de aceite:

- escrita permanece contida até apply aprovado;
- approval tem consumo único ou regra clara de validade;
- termos review, promoção e apply aparecem separados na UI/docs.

## pr 66: primeiro adapter governado

Escopo:

- escolher um adapter pequeno e testável;
- validar contrato de capacidades e falhas;
- preferir MCP ou CLI local simples;
- não iniciar ainda n8n, browser completo ou voz.

Condição de aceite:

- adapter não decide política;
- adapter só executa capacidades concedidas;
- falhas e tentativas de abuso ficam registradas.

## depois da fila

Depois dos seis PRs:

- browser adapter;
- n8n adapter;
- voice mvp;
- model lab;
- social/career automations;
- document/media agent.
