# permission model

## objetivo

Definir como o LAI classifica risco, concede capacidades e exige aprovação humana.

## regra central

Capacidades solicitadas não são capacidades concedidas.

A única fonte de autorização é a policy central aplicada pelo `permission_engine`.

## níveis de risco

A escala abaixo classifica impacto, mas não concede autorização automaticamente.

```text
risco_0: conversa e raciocínio sem ferramenta
risco_1: leitura local segura
risco_2: escrita em sandbox
risco_3: execução local sem sudo
risco_4: instalação, sudo, rede sensível, credenciais ou browser logado
risco_5: publicação, mensagens, candidaturas, formulários, compras ou ações irreversíveis
```

## capacidades iniciais

```text
filesystem_read
filesystem_write_sandbox
filesystem_apply
shell_readonly
shell_exec
sudo
network
browser_public
browser_authenticated
credentials_use
webhook_trigger
n8n_workflow
publish_content
send_message
submit_form
delete_data
external_private_data_send
```

## envelope de autorização

Toda autorização deve registrar:

```text
usuário
cliente
agente
serviço
ação
recurso
alvo
projeto
escopo
validade
conteúdo_ou_patch
consequência
decisão
```

Decisões possíveis:

```text
allow
ask
deny
```

## aprovação humana obrigatória

Sempre exigir aprovação humana para:

```text
apply da sandbox para projeto real
instalar ou remover software
usar sudo
alterar configuração de sistema, rede ou permissões
acessar ou usar credenciais
usar browser autenticado
publicar conteúdo
enviar mensagens
submeter candidatura ou formulário
confirmar compra
excluir dados fora da sandbox
enviar dados privados para serviço externo
ativar ou alterar automação com efeito sensível
ampliar permissão de ferramenta, plugin ou workflow
```

## negação por padrão

O sistema deve negar ou pedir esclarecimento quando:

- alvo não estiver claro;
- escopo não estiver claro;
- validade não estiver definida;
- ferramenta solicitar capacidade maior que a concedida;
- resultado anterior for desconhecido;
- conteúdo externo tentar alterar regras;
- a ação puder causar efeito externo não previsto.

## memória não autoriza

Memória pessoal, memória de projeto, arquivo, documento, código, página web ou saída de ferramenta pode informar contexto.

Nenhum desses conteúdos equivale a autorização.

## shell não é leitura segura por declaração

Um perfil chamado read-only não basta. Shell local pode produzir efeitos mesmo sem sudo.

O sistema deve separar pelo menos:

```text
shell_readonly
shell_exec
sudo
network
filesystem_write
```

## auditoria mínima

Toda decisão de ferramenta deve registrar:

```text
timestamp
usuário
cliente
agente
modo
domínio
canal
autonomia
capacidade_solicitada
capacidade_concedida
ação
alvo
decisão
motivo
resultado
```
