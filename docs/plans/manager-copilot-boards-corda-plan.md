<!--
ARQUIVO: plano C.O.R.D.A. para alinhar os boards principais do manager ao padrao de copiloto operacional do OctoBOX.

POR QUE ELE EXISTE:
- evita corrigir cada board do manager como se fosse um caso isolado.
- unifica lane, hero e boards sob a mesma logica semantica.
- registra riscos de regressao e seguranca antes de mexer nos includes principais.

O QUE ESTE ARQUIVO FAZ:
1. define contexto, objetivo, riscos, direcao e ondas para os boards do manager.
2. separa mudanca de cerebro semantico de mudanca visual.
3. documenta cuidados de regressao, seguranca e validacao.

PONTOS CRITICOS:
- ids, anchors e data-panels dos boards sao hooks vivos e nao devem mudar.
- textos dinamicos devem nascer no snapshot, nao no template.
- nenhuma mudanca desta frente deve introduzir HTML raw, formatacao insegura ou CTA contraditorio entre lane e board.
-->

# Manager Copilot Boards C.O.R.D.A.

## C - Contexto

O manager tem hoje duas camadas de leitura operacional:

1. `command lane`
2. `boards principais`

A lane ja comecou a receber logica de copiloto operacional.
Os boards principais ainda mantinham titulos, copys e estados vazios hardcoded nos templates.

Isso cria duas verdades:

1. a lane prioriza e fala como decisao
2. o board continua falando como secao informativa

Arquivos ancora:

1. [../../operations/queries.py](../../operations/queries.py)
2. [../../templates/operations/includes/manager/manager_intake_board.html](../../templates/operations/includes/manager/manager_intake_board.html)
3. [../../templates/operations/includes/manager/manager_link_board.html](../../templates/operations/includes/manager/manager_link_board.html)
4. [../../templates/operations/includes/manager/manager_enrollment_link_board.html](../../templates/operations/includes/manager/manager_enrollment_link_board.html)
5. [../../templates/operations/includes/manager/manager_finance_board.html](../../templates/operations/includes/manager/manager_finance_board.html)

## O - Objetivo

Fazer os boards principais do manager seguirem o mesmo padrao do OctoBOX:

1. `sinal`
2. `impacto operacional`
3. `proxima acao`

Sucesso significa:

1. lane e boards contam a mesma historia.
2. templates deixam de decidir copy dinamica.
3. estados limpos falam com calma e estados pressionados falam com firmeza.
4. o manager entende em segundos onde agir primeiro.

## R - Riscos

### Regressao estrutural

1. mudar `id`, `href`, `data-panel` ou ordem dos hosts pode quebrar scroll, navegacao curta e hooks de JS.

### Regressao semantica

1. lane e board podem passar a divergir se cada um usar copy propria.

### Regressao operacional

1. estados limpos podem continuar soando urgentes, o que gera falsa pressao.

### Seguranca e integridade

1. textos novos nao devem usar `safe`, HTML raw ou interpolacao insegura no template.
2. o backend deve seguir entregando strings simples para o autoescape padrao do Django.
3. nao introduzir CTA que sugira uma acao destrutiva sem contexto operacional real.

Traducao simples:

1. nao basta trocar a placa do corredor
2. precisamos garantir que a porta, a fechadura e a seta continuam no mesmo lugar

## D - Direcao

Direcao oficial desta frente:

1. snapshot manda na semantica
2. template so renderiza
3. ids e anchors permanecem intactos
4. visual fica estavel nesta onda

Regra de ouro:

**se o texto muda com o estado do board, ele nao deve nascer no include.**

## A - Acoes

### Onda 1 - Inventario de headers hardcoded

Mapear nos 4 boards:

1. `eyebrow`
2. `title`
3. `copy`
4. `pill_label`
5. `pill_class`
6. `empty state`

### Onda 2 - Contrato de board content

Criar no snapshot:

1. `manager_board_content.intake`
2. `manager_board_content.links`
3. `manager_board_content.enrollment_links`
4. `manager_board_content.finance`

Cada bloco deve expor:

1. `header`
2. `empty`
3. `status_mode`
4. `key`

### Onda 3 - Refatoracao dos includes

Trocar hardcode local por consumo do contrato.

Nao mexer em:

1. `id`
2. `data-panel`
3. estrutura de tabela
4. rows internas

### Onda 4 - Validacao de consistencia

Checklist:

1. lane e board do mesmo dominio contam a mesma historia
2. estados limpos usam tom calmo
3. estados com pressao usam tom firme
4. nenhum template volta a decidir semantica dinamica

## Guardrails de seguranca e regressao

1. manter autoescape do Django intacto
2. nao usar `|safe`
3. nao interpolar HTML no payload
4. manter todos os anchors `#manager-*board`
5. manter `data-panel` e `manager-live-pill`
6. nao tocar em rows nem formulários nesta onda

## Check de sucesso

O plano esta funcionando quando:

1. a lane e os boards parecem parte da mesma torre de controle
2. o manager para de ler os boards como se fossem blocos burocraticos
3. a mudanca acontece sem quebrar hooks, ids ou runtime
