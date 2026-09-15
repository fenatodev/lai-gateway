# LAI alpha readiness

## status

Checklist para decidir quando o `lai-gateway` pode ser apresentado publicamente como alpha técnico.

## declaração permitida

O projeto pode ser descrito como:

```text
LAI Gateway alpha: Workbench local-first para conversa, dev assistido via Harness e fundação de execução governada por capabilities.
```

## declaração proibida neste estágio

Não declarar ainda que o LAI possui:

```text
browser agent completo
automação n8n real
voz operacional
MCP tool execution generalizado
automação social/carreira com envio real
processamento completo de documentos e mídia
instalação one-click para qualquer sistema
```

## pronto agora

```text
arquitetura documentada
CI verde em Python 3.11 e 3.12
Workbench local com três modos
harness/gateway separados
chat comum sem run automático
session/runs read-only
local-chat workbench com review/promotion
policy/capability chain
audit events e log local sanitizado
dispatcher com primeiro adapter local seguro
mobile/private mode com pareamento e tokens em memória
Telegram outbound controlado
```

## lacunas antes de alpha público

```text
README precisa refletir pós-PR88 e roadmap atual
versão precisa ser planejada para 0.2.0-alpha ou equivalente
quickstart precisa ser testável por usuário novo
troubleshooting precisa cobrir harness ausente, token ausente e modelo ausente
promessas de adapters precisam ficar marcadas como contract ou planned
screenshots/guia visual do Workbench ainda faltam
release checklist público precisa existir
```

## critérios de go/no-go

### go para alpha técnico

```text
make check verde
CI verde
README alinhado ao roadmap
instalação local documentada
sem tokens ou caminhos privados em superfícies públicas
browser/n8n/voz/social/documentos não vendidos como implementados
primeiro fluxo seguro demonstrável no Workbench
```

### no-go

```text
qualquer adapter sensível executável sem approval gate
qualquer uso de shell genérico no caminho de adapter
README prometendo funcionalidade não implementada
release sem instrução de instalação limpa
publicação com versão ambígua
falha de CI ou publication scan
```

## decisão atual

Pós-PR88, o projeto está apto a virar alpha técnico depois de documentação pública, quickstart e versionamento. Ainda não está apto a ser chamado de produto completo.
