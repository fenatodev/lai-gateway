# PR 68 — browser adapter contract

## Objetivo

Registrar o browser adapter como contrato governado antes de qualquer automação de navegador.

## Escopo

- declarar domínio, canais, autonomia e capacidades solicitadas do browser adapter;
- manter `granted_capabilities` vazio no registry;
- deixar explícito que o adapter não executa browser, rede, login ou formulários;
- exigir aprovação humana para navegação pública, browser autenticado e efeitos externos.

## Fora de escopo

- abrir navegador real;
- automatizar login;
- preencher formulário;
- clicar em site externo;
- fazer scraping ou pesquisa web;
- integrar Playwright/Selenium.
