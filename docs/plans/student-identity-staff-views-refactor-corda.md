<!--
ARQUIVO: C.O.R.D.A. da refatoracao estrutural de `student_identity/staff_views.py`.

TIPO DE DOCUMENTO:
- plano arquitetural de refatoracao
- contrato operacional de execucao
- ponte entre arquitetura e prompting

AUTORIDADE:
- alta para a frente de refatoracao do corredor operacional de ativacao do aluno

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando a duvida for como desinchar `student_identity/staff_views.py` sem quebrar o runtime
- quando precisarmos separar politicas por papel de regras por capacidade
- quando quisermos executar a obra em ondas pequenas com guardrails de compatibilidade

POR QUE ELE EXISTE:
- evita separar o arquivo por role cedo demais e duplicar regra de negocio
- alinha arquitetura, debug, performance e prompting na mesma lingua
- cria um trilho unico para transformar `staff_views.py` em corredores reais de ownership

PONTOS CRITICOS:
- esta frente nao e reescrita de tela; e evolucao segura
- a URL e a experiencia publica precisam continuar estaveis durante a transicao
- role deve funcionar como policy, nao como deposito de regra duplicada
- queries, workflows e recommendations so entram onde melhoram clareza real
-->

# C.O.R.D.A. - Refatoracao estrutural de `student_identity/staff_views.py`

## C - Contexto

Hoje o corredor operacional de ativacao do aluno ja deixou de ser apenas uma tela simples de convite.

Ele agora concentra:

1. criacao de convite individual
2. criacao e pausa de link em massa
3. envio por e-mail
4. handoff de WhatsApp
5. aprovacao de membership
6. suspensao, reativacao e revogacao
7. troca de e-mail
8. fila quente
9. observabilidade
10. funis por jornada
11. recomendacao operacional
12. policy matrix por papel

Fotografia atual:

1. [../../student_identity/staff_views.py](../../student_identity/staff_views.py) tem mais de 1400 linhas
2. o arquivo gira em torno de uma unica view principal
3. essa view mistura policy, escrita, leitura pesada e heuristica operacional
4. o template [../../templates/student_identity/operations_invites.html](../../templates/student_identity/operations_invites.html) ainda representa uma superficie compartilhada com gate por permissao, nao cinco produtos separados por role

Leitura arquitetural correta:

1. o problema principal nao e "muitas roles"
2. o problema principal e "muitas capacidades diferentes no mesmo corredor HTTP"

Em linguagem simples:

1. hoje a portaria, a recepcao, a torre de controle e o painel de voos estao na mesma sala
2. separar a sala por tipo de pessoa cedo demais nao resolve a mistura das funcoes

## O - Objetivo

Refatorar `student_identity/staff_views.py` para uma arquitetura por capacidades, mantendo a superficie atual funcionando e deixando role no lugar certo: como policy e visibilidade, nao como deposito de regra.

### Sucesso significa

1. a URL e o template principal continuam estaveis durante a transicao
2. policies por role ficam explicitas e isoladas
3. acoes de invite, membership e delivery saem da view monolitica
4. leituras pesadas do page context saem para queries dedicadas
5. recomendacoes e funis saem para um corredor proprio
6. debug fica mais curto porque cada bug passa a ter um corredor natural de ownership
7. a base fica pronta para, no futuro, ganhar superficies realmente proprias por role se isso se tornar necessario

### Nao e objetivo desta frente

1. reescrever a UX da central de ativacao
2. criar uma tela separada por role agora
3. migrar models de forma agressiva
4. introduzir CQRS completo por moda
5. trocar a URL publica da operacao

## R - Riscos

### 1. Risco de separar por role cedo demais

Se o primeiro corte for `owner_views.py`, `manager_views.py`, `coach_views.py` etc.:

1. a mesma regra de approve, revoke ou open-whatsapp pode ser duplicada
2. o bug deixa de ter uma casa unica
3. o sistema parece mais organizado, mas fica mais caro de manter

### 2. Risco de mover bagunca de lugar

Se a obra apenas quebrar o arquivo grande em varios arquivos sem ownership real:

1. o projeto ganha mais nomes
2. mas continua com a mesma confusao

### 3. Risco de criar arquitetura teatral

Se introduzirmos `queries`, `workflows`, `recommendations` e `policies` sem criterio:

1. a leitura fica mais cerimonial
2. sem ganho proporcional de clareza

### 4. Risco de quebrar contrato de operacao

Se a URL, os nomes de `action` do POST ou o shape do contexto mudar cedo demais:

1. a tela pode continuar carregando
2. mas os circuitos reais de operacao quebram sem ruido suficiente

### 5. Risco de performance piorar

Se a separacao gerar recomposicao repetida de contexto ou queries duplicadas:

1. a arquitetura parece mais bonita
2. mas a tela fica mais lenta

Regra do predio:

1. se a obra fica mais elegante e mais lenta, piorou

## D - Direcao

### Tese central

O melhor corte aqui e:

1. policy por role
2. capacidade por corredor
3. view HTTP fina
4. leitura pesada fora da view
5. recomendacao operacional fora da montagem HTTP

### Frases de arquitetura

1. Role deve ser policy, nao deposito de regra.
2. Capacidade deve ser ownership, nao detalhe acidental.
3. View deve coordenar HTTP, nao concentrar dominio.
4. Query entra quando a leitura da pagina fica densa ou repetida.
5. Workflow entra quando a escrita tem regra, auditoria ou side effect.
6. Recommendation entra quando a inteligencia operacional deixa de ser apenas adornamento da view.

### Estrutura-alvo

```text
student_identity/
  staff_views/
    __init__.py
    base.py
    operations_page_view.py
    policies.py
    invite_action_views.py
    membership_action_views.py
    delivery_action_views.py
  queries/
    invitation_operations_queries.py
  workflows/
    invitation_management_workflows.py
    membership_management_workflows.py
    delivery_workflows.py
  recommendations/
    invitation_operations_recommendations.py
```

### Ownership-alvo por corredor

#### `staff_views/policies.py`

Responsavel por:

1. `build_access_matrix`
2. regras de coach, reception, manager, owner e dev
3. gates de quem pode operar qual acao

Nao deveria carregar:

1. queries pesadas
2. mutacao de membership
3. heuristica de recomendacao

#### `staff_views/invite_action_views.py`

Responsavel por:

1. create invite
2. create box link
3. pause box link
4. wiring de rate limit e anomaly alert

#### `staff_views/membership_action_views.py`

Responsavel por:

1. approve membership
2. suspend membership
3. reactivate membership
4. revoke membership
5. eventual troca de e-mail se continuar colada ao ciclo de identidade

#### `staff_views/delivery_action_views.py`

Responsavel por:

1. send email
2. open whatsapp
3. erros de entrega

#### `queries/invitation_operations_queries.py`

Responsavel por:

1. recent invites
2. stalled invites
3. pending memberships
4. managed memberships
5. observability cards
6. active box invite link snapshot

#### `recommendations/invitation_operations_recommendations.py`

Responsavel por:

1. journey funnels
2. priority of day
3. recommended queue
4. next action por jornada

#### `staff_views/operations_page_view.py`

Responsavel por:

1. coordenar GET e POST da superficie atual
2. despachar a acao para o corredor certo
3. montar o contexto final usando queries, policies e recommendations

### Decisao sobre split por role

#### Nao fazer agora

Nao separar o primeiro corte por role.

Por que:

1. a superficie atual ainda e compartilhada
2. o coach hoje e mais observer mode do que produto separado
3. owner, manager e reception ainda dividem muito fluxo
4. o corte por role agora teria alto risco de duplicar regra

#### Fazer depois, se o produto pedir

Separacao por role passa a fazer sentido quando:

1. cada role tiver rota quase propria
2. cada role tiver payload ou template quase proprio
3. a regra compartilhada entre roles cair bastante

### Direcao de performance

Pela lente de performance:

1. o split deve reduzir leitura repetida dentro de `get_context_data`
2. `select_related` e `prefetch_related` precisam continuar preservados ou melhorar
3. o page context deve caminhar para snapshots de leitura claros
4. a recomendacao operacional nao deve disparar queries ocultas em cascata

Metas qualitativas:

1. nenhuma regressao visivel no carregamento da tela
2. menos chance de N+1 acidental
3. menor custo mental para otimizar depois

### Direcao de debug

Pela lente de debug:

1. bug de permissao deve apontar para `policies.py`
2. bug de approve/suspend/revoke deve apontar para `membership_action_views.py` ou workflow associado
3. bug de convite deve apontar para `invite_action_views.py`
4. bug de fila recomendada deve apontar para `recommendations/`

Em linguagem de detective:

1. cada crime precisa ter um bairro natural para investigar
2. hoje a cidade inteira responde pelo mesmo endereco

## A - Acoes

### Onda 0 - Inventario e cinturão de segurança

Objetivo:

1. preparar a obra sem trocar a porta do predio

Acoes:

1. mapear os blocos do arquivo atual por capacidade
2. mapear os `action` values do POST
3. mapear testes existentes e lacunas do circuito
4. registrar o shape minimo do contexto usado no template

Criterio de pronto:

1. sabemos qual bloco atual vai para qual corredor
2. sabemos o que nao pode quebrar durante a transicao

### Onda 1 - Extrair policy

Objetivo:

1. tirar role logic da view principal

Acoes:

1. criar `staff_views/policies.py`
2. mover `build_access_matrix`
3. mover gates de permissao reutilizaveis

Criterio de pronto:

1. policies ficam explicitas
2. a view fica menos confusa sem mudar comportamento

### Onda 2 - Extrair actions por capacidade

Objetivo:

1. separar escrita mutavel da view monolitica

Acoes:

1. criar `invite_action_views.py`
2. criar `membership_action_views.py`
3. criar `delivery_action_views.py`
4. manter os mesmos nomes de `action` do POST

Criterio de pronto:

1. os handlers deixam de viver todos no mesmo arquivo
2. a URL continua a mesma

### Onda 3 - Extrair queries da pagina

Objetivo:

1. separar leitura pesada do page context

Acoes:

1. criar `queries/invitation_operations_queries.py`
2. mover montagem de recent invites, stalled invites, pending memberships, managed memberships e observability
3. revisar `select_related` e `prefetch_related`

Criterio de pronto:

1. `get_context_data` vira coordenacao leve
2. o shape entregue ao template continua compativel

### Onda 4 - Extrair recommendations

Objetivo:

1. tirar heuristica operacional do corredor HTTP

Acoes:

1. criar `recommendations/invitation_operations_recommendations.py`
2. mover journey funnels
3. mover priority of day
4. mover recommended queue

Criterio de pronto:

1. inteligencia operacional para de morar no mesmo arquivo da action HTTP

### Onda 5 - Reavaliar split visual por role

Objetivo:

1. decidir com evidencia se a superficie precisa ou nao de corte por role

Acoes:

1. medir o quanto de payload e acao ainda e compartilhado
2. avaliar se coach virou de fato uma experiencia propria
3. avaliar se owner/manager/reception pedem fachadas realmente distintas

Criterio de pronto:

1. a decisao de separar ou nao por role deixa de ser opiniao e vira leitura de produto

## Prompt Overlay da frente

Este plano combina duas camadas:

1. `$software-architecture-chief` define a direcao estrutural e os trade-offs
2. `$prompt-engineer` define o contrato de execucao para que cada onda seja reproduzivel e auditavel

### Prompt Spec da frente

#### Objetivo

Refatorar `student_identity/staff_views.py` em corredores de capacidade, preservando comportamento, URL atual e superficie compartilhada enquanto a transicao acontece.

#### Inputs

1. runtime atual
2. docs canonicos de arquitetura
3. testes existentes
4. este C.O.R.D.A.

#### Nao objetivos

1. reescrever a UX da central
2. criar uma tela nova por role agora
3. trocar models ou contratos externos sem necessidade
4. introduzir camadas vazias sem ganho real

#### Constraints

1. manter compatibilidade
2. nao duplicar regra por role
3. nao piorar query count ou latencia de forma perceptivel
4. preservar os nomes de `action` no POST
5. preservar o shape essencial de contexto consumido pelo template

#### Output contract

Cada onda deve entregar:

1. arquivos criados ou movidos
2. comportamento preservado
3. risco principal da onda
4. validacao executada
5. debito tecnico evitado ou criado

#### Failure checks

Antes de considerar a onda pronta, verificar:

1. a mudanca criou ownership real ou apenas espalhou codigo?
2. alguma regra ficou duplicada entre roles?
3. alguma query passou a rodar em dobro?
4. o template continuou consumindo o mesmo contrato?
5. algum bug de permissao ficou mais dificil de localizar?

## Prompt operacional reutilizavel

Use este prompt nas proximas ondas desta frente:

```md
Voce esta executando a frente `student-identity-staff-views-refactor-corda`.

Objetivo:
Refatorar `student_identity/staff_views.py` por corredores de capacidade, preservando comportamento, URL e experiencia atual.

Contexto:
- O projeto segue a tese de `modular monolith`.
- Role deve funcionar como policy, nao como deposito de regra duplicada.
- A superficie atual ainda e compartilhada; split por role nao e o primeiro corte.
- Esta execucao deve seguir o C.O.R.D.A. `docs/plans/student-identity-staff-views-refactor-corda.md`.

Escopo desta execucao:
- [descreva aqui a onda atual]

Constraints:
- nao reescrever a UX
- nao trocar a URL publica
- nao mudar nomes de `action` do POST sem aprovacao explicita
- nao criar abstractions vazias
- nao piorar query count ou latencia de forma perceptivel
- manter foco em compatibilidade

Entrega obrigatoria:
1. mudancas de codigo
2. risco principal da onda
3. validacao executada
4. debito tecnico evitado ou criado
5. observacoes sobre se o corte por role continua ou nao injustificado
```

## Criterio final de sucesso

Ao final desta frente:

1. `student_identity/staff_views.py` deixa de ser o endereco unico de tudo
2. policy, action, query e recommendation passam a ter corredores claros
3. a superficie atual continua operando sem regressao
4. bugs por permissao, convite, membership e recomendacao ficam muito mais curtos de localizar
5. o sistema fica pronto para, no futuro, separar superficies por role apenas se o produto realmente pedir isso
