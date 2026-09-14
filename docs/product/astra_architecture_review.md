# astra architecture review

## resumo executivo

A revisão do Astra validou a direção geral do LAI, mas apontou uma falha de arquitetura importante: o plano inicial misturava domínio, canal, capacidade e autonomia como se fossem o mesmo tipo de "modo". Essa mistura pode causar roteamento ambíguo e permissões indevidas.

A correção adotada para o próximo plano é separar internamente quatro dimensões:

```text
domínio: dev, social, carreira, segurança, documentos, mídia
canal: vscode, workbench, web ui, telegram, voz
autonomia: conversa, leitura, proposta, execução, apply
capacidade: filesystem, shell, browser, rede, publicação, credenciais
```

Trocar de domínio ou canal nunca deve elevar permissões automaticamente.

## riscos principais identificados

1. A escala simples de permissões é insuficiente. Execução sem sudo ainda pode apagar dados, acessar credenciais ou produzir efeitos externos.
2. Harness, terminal, browser e n8n podem contornar aprovação se cada motor controlar suas próprias permissões.
3. Modos misturados geram ambiguidade entre interface, domínio, capacidade e autonomia.
4. Fronteiras do core ainda precisam de contratos claros e direção de dependência.
5. Falta definir estado persistente local para aprovações, memória, execução, recuperação e idempotência.

## decisões validadas

1. Conversa comum deve ser conversation-first e não deve iniciar harness.
2. Planejamento/leitura deve ser separado de alteração/apply.
3. O LAI deve reutilizar motores especializados em vez de recriar tudo.
4. Skills pequenas, composáveis e versionadas são o caminho certo.
5. Voz, n8n e browser devem ser capacidades integradas ao LAI, não cores paralelos.

## mudanças obrigatórias antes de codar features grandes

1. Separar domínio, canal, autonomia e capacidade.
2. Trocar autorização baseada apenas em níveis por autorização baseada em capacidades delimitadas.
3. Definir ciclo único de ação: proposta, autorização, execução, revisão e conclusão.
4. Fixar contratos do core e dos adapters.
5. Definir persistência local como fonte de verdade para memória, aprovações e execuções.
