# pr 71: model lab contract

## objetivo

Registrar o model lab como contrato governado antes de qualquer download de modelo, benchmark pesado, alteração de runtime ou execução de servidor local de modelo.

## escopo

- adicionar model_lab ao adapter registry;
- declarar domínio, canais, autonomia e capacidades solicitadas;
- manter granted_capabilities vazio;
- manter download de modelos, benchmarks, mutação de runtime, rede e credenciais desabilitados;
- exigir aprovação humana para download, benchmark, acesso a GPU, alteração de runtime, upload de resultados e escrita em filesystem.

## fora de escopo

- sem baixar modelos;
- sem rodar benchmark pesado;
- sem iniciar runtime ou servidor de modelo;
- sem alterar configuração ativa de runtime;
- sem uso de GPU;
- sem envio de resultados para serviço externo;
- sem decisão automática de modelo padrão.

## aceite

- registry expõe o contrato model_lab;
- model_lab não executa tools e não concede permissões;
- testes comprovam que downloads, benchmarks, runtime mutation, rede e credenciais permanecem desligados;
- make check passa.
