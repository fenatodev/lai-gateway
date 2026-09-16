# Objective state local

`objective-state/v1` é o registro local read-only de objetivo, tarefas e checkpoints de um projeto LAI.

Ele existe para dar contexto operacional explícito antes de propostas, aprovações e execução local. Ele não cria autorização, não consome grants, não executa adapters e não transforma conteúdo do projeto em instrução confiável.

## Entrada explícita

O operador deve informar uma `workspace_root` explícita; em outras palavras, uma workspace_root explícita. O arquivo de estado padrão é `.lai/objective-state.json`, sempre relativo ao workspace.

O coletor deve rejeitar:

- `workspace_root` ausente, fora do escopo configurado ou symlink.
- `state_file` absoluto.
- `state_file` com traversal.
- symlink em qualquer parte do caminho do arquivo.
- arquivo acima do limite local.
- JSON inválido.
- conteúdo com formato de segredo.

## Forma do arquivo

```json
{
  "schema_version": "objective-state/v1",
  "project_id": "lai-gateway",
  "objective": "Alpha operacional local",
  "status": "active",
  "tasks": [
    {
      "id": "pr113",
      "title": "Objective state read-only",
      "status": "doing",
      "domain": "project",
      "channel": "workbench",
      "autonomy": "high",
      "capability": "objective-state",
      "target": ".lai/objective-state.json",
      "risk": "low"
    }
  ],
  "checkpoints": [
    {
      "id": "cp1",
      "summary": "PR112 merged",
      "created_at_utc": "2026-09-16T19:46:46Z"
    }
  ]
}
```

## Saída

A saída deve declarar:

- `schema_version: objective-state/v1`.
- `operation: objective-state`.
- `overall`: `ready`, `needs_state` ou `blocked`.
- `data_touched`: workspace explícito, arquivo relativo, leitura de conteúdo, ausência de scan recursivo e ausência de escrita.
- `security`: read-only, conteúdo não confiável, sem autorização inferida, sem grants, sem adapter dispatch, sem execução, sem rede e sem ingestão implícita.

## Limites

Conteúdo lido do estado continua não confiável. O estado é informativo. Ele pode orientar a próxima proposta, mas não autoriza a proposta nem a execução. Uma tarefa com `autonomy: high` continua sendo apenas dado recuperado. O runtime deve tratar cada campo como conteúdo não confiável até uma política efetiva validar ação, alvo, parâmetros, identidade, validade e hash aplicável.
