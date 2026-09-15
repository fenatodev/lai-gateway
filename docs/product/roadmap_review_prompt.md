# LAI roadmap external review prompt

Use este prompt para revisar o roadmap com GPT-6, Codex, Astra ou outro revisor crítico.

```text
Você está revisando o roadmap do LAI.

Contexto:
- LAI é um sistema operacional pessoal de IA local, open-source-first e modular.
- Deve separar domínio, canal, autonomia e capacidade.
- Gateway coordena entrada, roteamento, modelo local e interfaces.
- Harness cuida de dev assistido, sandbox, review e apply.
- Skills, adapters, canais e conteúdo recuperado nunca concedem permissão.
- Browser, n8n, voz, documentos, social/career e MCP devem entrar por adapters governados.

Tarefa:
Revise o roadmap contra o objetivo final do LAI.
Não invente um produto novo.
Não sugira liberar automação externa antes dos gates.
```

```text
Avalie:
1. O roadmap aproxima o projeto do LAI definido?
2. Há dependências invertidas?
3. Há lacunas entre promessa e implementação?
4. Algum adapter sensível aparece cedo demais?
5. Alguma etapa mistura domínio, canal, autonomia ou capacidade?
6. Falta persistência, auditoria, autorização ou rollback antes de algum side effect?
7. Quais são os 10 próximos PRs recomendados, mantendo o escopo atual?
8. Quais PRs deveriam ser bloqueados até existirem gates melhores?
9. Quais frases do README/release seriam enganosas neste estágio?
10. Quais testes ou critérios de aceite faltam?

Formato da resposta:
- riscos críticos
- dependências invertidas
- lacunas de produto
- ajustes recomendados no roadmap
- próximos 10 PRs em ordem sugerida
- itens que não devem ser feitos ainda
```
