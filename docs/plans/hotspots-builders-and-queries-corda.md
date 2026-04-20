<!--
ARQUIVO: C.O.R.D.A. para os hotspots atuais de builders e queries do OctoBOX.

TIPO DE DOCUMENTO:
- plano arquitetural
- guia operacional por ondas
- contrato de execucao para refatoracao incremental

AUTORIDADE:
- alta para a reorganizacao dos hotspots atuais de leitura, heuristica e analytics

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [operations-queries-and-published-history-corda.md](operations-queries-and-published-history-corda.md)

QUANDO USAR:
- quando a duvida for quais hotspots atacar depois da limpeza das views
- quando quisermos refatorar builders e queries sem virar arquitetura teatral
- quando precisarmos de uma ordem de ondas que preserve latencia, contrato de tela e velocidade de entrega

POR QUE ELE EXISTE:
- evita que o projeto continue limpando portas HTTP enquanto o peso real migra para builders e queries centrais
- organiza a evolucao dos hotspots mais provaveis de crescer mal
- alinha arquitetura e performance numa unica lingua de execucao

O QUE ESTE ARQUIVO FAZ:
1. registra a fotografia atual dos hotspots mais importantes
2. define a ordem de ataque por ROI real
3. organiza a obra em ondas pequenas
4. documenta guardrails de performance e ownership
5. entrega blocos prontos de `/elite prompt` para execucao

PONTOS CRITICOS:
- arquivo grande sozinho nao e culpa; o problema e mistura de responsabilidades ou crescimento sem ownership
- o objetivo nao e modularizar por beleza, e sim abrir corredores onde a manutencao e o tuning fino ficaram caros
- se a arquitetura ficar mais bonita e a tela ficar mais lenta, a refatoracao falhou
-->

# C.O.R.D.A. - Hotspots de Builders e Queries

## C - Contexto

Depois das ultimas ondas, os principais hotspots do projeto deixaram de ser views pesadas e passaram a ser motores internos de leitura, heuristica e agregacao.

Hoje a fotografia mais importante e esta:

1. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)
2. [catalog/student_queries.py](../../catalog/student_queries.py)
3. [catalog/finance_snapshot/ai/analytics.py](../../catalog/finance_snapshot/ai/analytics.py)
4. [operations/manager_workspace_queries.py](../../operations/manager_workspace_queries.py)

Eles nao doem pelo mesmo motivo.

### `operations/workout_board_builders.py`

Estado observado:

1. modulo muito grande, com varias bancadas internas
2. mistura `review diff`, `preview do aluno`, `decision assist`, `signals executivos`, `rm gap queue` e `weekly checkpoint`
3. ja recebeu a primeira extração do corredor de `review`, mas ainda concentra muita inteligencia em um unico lugar

Em linguagem simples:

1. e uma oficina grande que ainda tem mecanica, pintura, eletrica e inspeção funcionando no mesmo galpao

### `catalog/student_queries.py`

Estado observado:

1. concentra listing snapshot, support snapshot, filtros, metricas, refresh token e leitura financeira do aluno
2. mistura leitura do diretorio com leitura da ficha financeira, que sao dois corredores mentais diferentes
3. e um hotspot claro de crescimento porque diretorio e ficha costumam receber regra nova o tempo inteiro

Em linguagem simples:

1. e um shopping de queries onde diretorio e ficha financeira ainda dividem o mesmo predio

### `catalog/finance_snapshot/ai/analytics.py`

Estado observado:

1. dominio coerente, mas alta densidade analitica
2. concentra recommendation performance, timing matrices, adherence/divergence learning e outcome learning
3. ainda nao e prioridade numero 1, mas ja e um hotspot provavel do proximo ciclo

Em linguagem simples:

1. e um laboratorio de analytics que ainda funciona bem, mas ja tem instrumentos demais na mesma mesa

### `operations/manager_workspace_queries.py`

Estado observado:

1. grande e denso
2. ainda coeso por corredor
3. nao precisa entrar na obra agora se os outros tres ainda renderem mais

Em linguagem simples:

1. e uma oficina grande, mas ainda organizada o suficiente para esperar

## O - Objetivo

Ganhar chao estrutural para o app continuar evoluindo sem que a complexidade migre das views para os builders e queries.

### Sucesso significa

1. `workout_board_builders.py` virar um orquestrador com bancadas claras
2. `student_queries.py` separar `directory` de `financial`, sem quebrar as fachadas publicas
3. `finance_snapshot/ai/analytics.py` ganhar um caminho claro de fatiamento antes de virar um novo monolito analitico
4. a performance nao piorar
5. a equipe conseguir localizar mais rapido onde mexer quando algo quebrar

## R - Riscos

### 1. Modularizar por ansiedade

Se abrirmos arquivos cedo demais:

1. aumenta a cerimonia
2. reduz a velocidade
3. sem diminuir o risco real

Traducao infantil:

1. e como comprar um armario inteiro para guardar duas colheres

### 2. Perder latencia no meio da obra

Esse risco e central pela lente do `$OctoBox High Performance Architect`.

Se movermos leitura sem cuidar de:

1. agregacao
2. `select_related/prefetch_related`
3. snapshots
4. reuso de queryset

o sistema pode ficar mais bonito e mais lento.

Regra:

1. arquitetura sem velocidade nao serve ao modelo do OctoBox

### 3. Misturar tipo de corredor

Se diretorio de alunos e ficha financeira continuarem nascendo do mesmo lugar:

1. uma regra de listagem passa a tocar a leitura financeira sem necessidade
2. o tuning fino fica mais caro

### 4. Quebrar contrato publico

As fachadas publicas existentes precisam continuar estaveis:

1. `build_student_directory_snapshot`
2. `build_student_financial_snapshot`
3. `build_published_workout_history`
4. payloads da board e do catalogo

### 5. Atacar o hotspot errado

`manager_workspace_queries.py` e grande, mas hoje nao e o melhor ROI.

Regra:

1. o proximo arquivo a entrar na obra precisa doer mais do que os outros

## D - Direcao

### Tese central

Refatorar por corredores internos de responsabilidade, mantendo as fachadas publicas enquanto as bancadas sao separadas por dentro.

### Regra-mestra

1. fachada publica preservada
2. corredor interno extraido
3. smoke real validado
4. proxima onda so entra depois

### Ordem recomendada

1. `operations/workout_board_builders.py`
2. `catalog/student_queries.py`
3. `catalog/finance_snapshot/ai/analytics.py`
4. `operations/manager_workspace_queries.py` somente se continuar crescendo

### Forma-alvo mental

```text
operations/
  workout_board_review_builders.py
  workout_board_management_builders.py
  workout_board_weekly_builders.py
  workout_board_builders.py

catalog/
  student_directory_queries.py
  student_financial_queries.py
  student_queries.py

catalog/finance_snapshot/ai/
  analytics_recommendation.py
  analytics_timing.py
  analytics_learning.py
  analytics.py
```

Observacao:

1. isso e forma-alvo mental
2. nao precisamos criar tudo agora
3. a regra e abrir poucos corredores por onda

### Guardrails arquiteturais

#### Para `workout_board_builders.py`

1. manter `workout_board_builders.py` como fachada/orquestrador
2. separar por bancadas internas, nao por helper aleatorio
3. ordem mais segura:
   - `review`
   - `management`
   - `weekly/executive`

#### Para `student_queries.py`

1. manter `student_queries.py` como fachada publica no inicio
2. separar primeiro `directory listing + support`
3. deixar `financial snapshot` por ultimo porque ele merece ownership proprio

#### Para `finance_snapshot/ai/analytics.py`

1. tratar como laboratorio analitico
2. separar por tipo de leitura:
   - recommendation performance
   - timing matrices
   - learning/divergence
3. so atacar depois que `student_queries.py` ficar assentado

### Guardrails de performance

Pela lente do `$OctoBox High Performance Architect`, cada onda deve explicitar:

1. quantas queries ela pode alterar
2. quais agregacoes precisam continuar centralizadas
3. quais snapshots/facades publicas nao podem duplicar trabalho
4. se o custo de CPU e serializacao subiu ou caiu

Regra de ouro:

1. se o modulo novo introduzir leitura duplicada, o corte foi ruim

## A - Acoes por ondas

## Onda 1 - `workout_board_builders.py` / corredor de review

Status atual:

1. ja iniciado
2. review diff, preview e decision assist ja sairam para [operations/workout_board_review_builders.py](../../operations/workout_board_review_builders.py)

Critério de pronto:

1. smoke da board verde
2. `workout_board_builders.py` mais legivel
3. nenhuma mudanca de contrato da board

## Onda 2 - `workout_board_builders.py` / corredor de management

Mover para algo como:

1. `build_operational_memory_patterns`
2. `build_operational_leverage_summary`
3. `build_operational_leverage_trends`
4. `build_operational_management_alerts`
5. `build_rm_readiness_management_alerts`
6. `build_rm_gap_queue`
7. `build_management_alert_priority`
8. `build_management_recommendations`

Modulo alvo sugerido:

1. [operations/workout_board_management_builders.py](../../operations/workout_board_management_builders.py)

Sucesso significa:

1. a leitura de management sair do miolo do builder principal
2. `rm gap` ganhar ownership claro

## Onda 3 - `workout_board_builders.py` / corredor weekly-executive

Mover para algo como:

1. `build_weekly_executive_summary`
2. `build_weekly_checkpoint_rhythm`
3. `build_weekly_checkpoint_maturity`
4. `build_weekly_governance_action`

Modulo alvo sugerido:

1. [operations/workout_board_weekly_builders.py](../../operations/workout_board_weekly_builders.py)

Sucesso significa:

1. weekly/executive virar uma bancada propria
2. `workout_board_builders.py` ficar predominantemente orquestrador

## Onda 4 - `catalog/student_queries.py` / directory listing

Mover para algo como:

1. `_build_student_directory_refresh_token`
2. `_build_student_directory_metrics`
3. `_build_student_directory_interactive_kpis`
4. `build_student_directory_listing_snapshot`

Modulo alvo sugerido:

1. [catalog/student_directory_queries.py](../../catalog/student_directory_queries.py)

Sucesso significa:

1. o diretorio de alunos ganhar corredor proprio
2. a performance do diretorio continuar protegida

## Onda 5 - `catalog/student_queries.py` / support snapshot

Mover para o mesmo modulo de `directory`:

1. `_build_student_directory_support_queryset`
2. `_build_student_directory_support_surfaces`
3. `build_student_directory_support_snapshot`

Sucesso significa:

1. support queue e diretorio viverem na mesma bancada
2. `student_queries.py` deixar de ser o shopping central do catalogo

## Onda 6 - `catalog/student_queries.py` / financial snapshot

Mover para algo como:

1. [catalog/student_financial_queries.py](../../catalog/student_financial_queries.py)

Escopo esperado:

1. `get_operational_enrollment`
2. `get_operational_payment_status`
3. `get_operational_payment_status_label`
4. `compute_fidalgometro_score`
5. `build_student_financial_snapshot`

Sucesso significa:

1. ficha financeira ganhar ownership real
2. `student_queries.py` virar fachada de composicao

## Onda 7 - `catalog/finance_snapshot/ai/analytics.py`

Somente depois das ondas acima.

Fatiamento recomendado:

1. `analytics_recommendation.py`
2. `analytics_timing.py`
3. `analytics_learning.py`
4. `analytics.py` como fachada/orquestrador

Regra:

1. so entra nesta obra se os hotspots anteriores estiverem assentados

## O que nao fazer agora

1. mexer em `operations/manager_workspace_queries.py` por reflexo
2. abrir micro-modulos de 20 linhas sem ownership real
3. trocar contratos publicos cedo
4. misturar tuning de performance com renomeacao cosmetica

## Blocos de `/elite prompt`

### Bloco 1 - Onda 2 do `workout_board_builders.py`

```text
/elite prompt
Objetivo: executar a Onda 2 de `operations/workout_board_builders.py`, extraindo o corredor de management sem mudar comportamento.

Contexto:
- `review` ja foi extraido para `operations/workout_board_review_builders.py`
- agora o alvo e tirar de `workout_board_builders.py` o miolo de `operational memory`, `leverage`, `rm readiness`, `rm gap queue` e recomendacao de management
- manter `workout_board_builders.py` como fachada/orquestrador

Restricoes:
- nao mudar contrato publico das funcoes chamadas pela board
- nao criar arquitetura teatral
- preservar performance e evitar duplicacao de leitura
- validar com `tests.test_workout_approval_board` e `tests.test_workout_post_publication_history`

Saida esperada:
1. novo modulo de management builders
2. imports atualizados no builder principal
3. smoke real executado
4. resumo curto do que mudou e do risco residual
```

### Bloco 2 - Onda 4 de `catalog/student_queries.py`

```text
/elite prompt
Objetivo: executar a Onda 4 de `catalog/student_queries.py`, extraindo o corredor de `directory listing` para um modulo proprio sem quebrar a fachada publica.

Contexto:
- `student_queries.py` hoje mistura diretorio, support snapshot e ficha financeira
- a prioridade agora e `directory listing + metrics + refresh token`
- a fachada publica atual deve continuar existindo

Restricoes:
- preservar performance do diretorio
- nao aumentar queries do caminho principal sem justificativa
- manter `build_student_directory_snapshot` funcionando
- validar com smoke de catalog e testes de performance relacionados ao diretorio

Saida esperada:
1. novo modulo `student_directory_queries.py`
2. fachada publica preservada
3. smoke real executado
4. resumo curto com antes/depois arquitetural
```

### Bloco 3 - Onda 6 de `catalog/student_queries.py`

```text
/elite prompt
Objetivo: executar a Onda 6 de `catalog/student_queries.py`, levando a ficha financeira para um corredor proprio com ownership claro.

Contexto:
- o diretorio ja deve ter saído antes desta onda
- agora o alvo e o corredor de `financial snapshot`
- a ideia e separar leitura do diretorio da leitura da ficha do aluno

Restricoes:
- manter a assinatura publica de `build_student_financial_snapshot`
- nao misturar novamente financeiro com support snapshot
- preservar comportamento da ficha do aluno
- validar com smoke de catalog

Saida esperada:
1. novo modulo `student_financial_queries.py`
2. `student_queries.py` mais fino
3. smoke real executado
4. resumo curto do ganho arquitetural
```

## Fechamento

Este CORDA existe para impedir um erro comum:

1. limpar views e achar que a obra acabou

Na pratica, o peso mais perigoso do app agora esta migrando para:

1. builders
2. queries
3. analytics compostos

Em linguagem simples:

1. ja organizamos a portaria e os corredores principais
2. agora estamos arrumando a central de motores da casa
3. se fizermos isso por ondas, o app continua crescendo com estrutura
4. se fizermos isso por impulso, trocamos um tipo de bagunca por outro
