<!--
ARQUIVO: C.O.R.D.A. de refatoracao estrutural de `operations/queries.py` e `operations/workout_published_history.py`.

TIPO DE DOCUMENTO:
- plano arquitetural
- guia operacional por ondas
- contrato de execucao para refatoracao incremental

AUTORIDADE:
- alta para a reorganizacao desses corredores de leitura operacional

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)

QUANDO USAR:
- quando a duvida for como emagrecer `operations/queries.py` sem quebrar o workspace operacional
- quando precisarmos separar leitura, heuristica, payload e copy no historico publicado do WOD
- quando quisermos executar a obra por ondas pequenas, com seguranca de manutencao e sem arquitetura teatral

POR QUE ELE EXISTE:
- evita que `operations/queries.py` continue crescendo como um deposito unico de papeis, cards, serializers e heuristicas
- cria uma fundacao mais previsivel para owner, manager, coach e reception
- reduz o risco de `workout_published_history.py` virar um segundo arquivo-elefante
- alinha arquitetura, front e performance numa unica lingua de execucao

O QUE ESTE ARQUIVO FAZ:
1. registra a fotografia atual dos dois hotspots
2. define a arquitetura-alvo sem rewrite
3. organiza a migracao por ondas pequenas
4. documenta guardrails de performance e contrato de tela
5. entrega prompts de execucao para a frente

PONTOS CRITICOS:
- arquivo grande sozinho nao prova lentidao, mas prova risco de crescimento ruim
- a prioridade aqui e separar ownership de responsabilidade, nao espalhar helper por esporte
- a fachada visual e os payloads nao devem quebrar durante a transicao
-->

# C.O.R.D.A. - Refatoracao de `operations/queries.py` e `operations/workout_published_history.py`

## C - Contexto

Hoje existem dois hotspots diferentes dentro de `operations/`:

1. [operations/queries.py](../../operations/queries.py)
2. [operations/workout_published_history.py](../../operations/workout_published_history.py)

Eles nao doem pelo mesmo motivo.

### `operations/queries.py`

Estado observado:

1. arquivo com mais de 1500 linhas
2. mistura leitura por papel com serializers, CTA, copy e heuristica de prioridade
3. concentra owner, manager, coach, reception e dev no mesmo corredor
4. em especial, `manager` e `reception` ja carregam leitura operacional, hints de interface e decisao contextual no mesmo modulo

Em linguagem simples:

1. esse arquivo virou um shopping inteiro com loja, caixa, vitrine e estoque no mesmo predio

### `operations/workout_published_history.py`

Estado observado:

1. arquivo com mais de 700 linhas
2. ainda respeita um dominio unico: leitura pos-publicacao do WOD
3. ja mistura query, runtime metrics, RM readiness, follow-up, escalada e executive summary
4. o risco maior nao e caos imediato, e sim virar um segundo monolito denso se continuar crescendo no mesmo ritmo

Em linguagem simples:

1. ainda e uma oficina so, mas ja tem bancada demais dentro do mesmo comodo

### Leitura oficial do problema

Pelo modelo do OctoBox:

1. borda HTTP deve ser fina
2. leitura reutilizavel deve ficar em corredores claros
3. copy/payload nao deve contaminar query de forma irreversivel
4. crescimento deve privilegiar modular monolith, nao mini-frameworks internos

### Tese do problema

O risco principal aqui nao e "Python demora para abrir arquivo grande".

O risco principal e:

1. ownership confuso
2. manutencao cara
3. dificuldade de tuning fino por corredor
4. regressao silenciosa quando uma mudanca local encosta em outros papeis
5. dificuldade de explicar onde termina leitura e onde comeca heuristica ou apresentacao

## O - Objetivo

Refatorar os dois hotspots sem rewrite para que:

1. `operations/queries.py` deixe de ser um deposito multirrole
2. cada papel importante tenha corredor de leitura claro
3. `workout_published_history.py` fique fatiado por responsabilidade interna, sem perder coesao de dominio
4. a performance nao piore
5. o contrato visual e o page payload continuem estaveis durante a obra

### Sucesso significa

1. alterar `reception` nao exige navegar o mesmo arquivo de `owner`, `coach` e `manager`
2. `manager` e `reception` ganham leitura e copy mais localizadas
3. `workout_published_history.py` fica dividido em `metrics/readiness`, `follow-up/escalation` e `executive summary`
4. novos cards ou regras entram no corredor certo, e nao no "arquivo onde cabe"
5. a obra melhora o mapa da casa em vez de criar mais portas sem placa

## R - Riscos

### 1. Refatorar por tamanho e nao por capacidade

Se quebrarmos `queries.py` por pedaços arbitrarios:

1. o arquivo encolhe
2. mas a responsabilidade continua confusa

Traducao infantil:

1. e como espalhar os brinquedos em mais caixas sem separar carrinho de lego

### 2. Criar arquitetura teatral

Se abrirmos arquivos demais cedo:

1. o projeto ganha cerimônia
2. o ganho real nao paga o custo

Antialvo:

1. 12 modulos novos para mover helpers de 5 linhas

### 3. Piorar performance durante a obra

Se mover leitura sem cuidar de prefetch e snapshot:

1. aumentamos queries
2. duplicamos agregacao
3. degradamos o tempo de resposta

### 4. Quebrar o contrato visual

Se payload mudar sem disciplina:

1. templates e JS quebram
2. o front fica dependente de renomeacao interna

### 5. Misturar front concern em query concern

Copy, tom visual e classe CSS podem existir perto da leitura, mas nao podem sequestrar a modelagem de query.

Regra:

1. query prepara dado
2. presenter/context fecha o contrato da tela

## D - Direcao

### Tese central

Refatorar por corredores de responsabilidade e por capacidade real.

### Regra-mestra

1. query le
2. context/presenter organiza
3. action muta
4. heuristica cresce em modulo proprio quando vira corredor

### Arquitetura-alvo recomendada

```text
operations/
  owner_workspace_queries.py
  manager_workspace_queries.py
  reception_workspace_queries.py
  coach_workspace_queries.py
  dev_workspace_queries.py
  workspace_cta_presenters.py
  workout_publication_metrics.py
  workout_publication_follow_up.py
  workout_publication_executive.py
  workout_published_history.py
```

Observacao:

1. essa e a forma-alvo mental
2. nao precisamos criar tudo de uma vez
3. o principio e abrir poucos corredores por onda, com ownership claro

### Ownership recomendado

#### `operations/queries.py`

Deve perder volume para corredores por papel, na seguinte ordem:

1. `manager`
2. `reception`
3. `owner`
4. `coach`
5. `dev`

Motivo:

1. `manager` e `reception` sao os trechos mais densos e mais propensos a crescer
2. `owner` ja tem copy e metric cards misturados, mas cresce mais devagar
3. `coach` e `dev` estao grandes, porem menos quentes

#### `operations/workout_published_history.py`

Deve ser fatiado assim:

1. `workout_publication_metrics.py`
   - runtime metrics
   - RM readiness
2. `workout_publication_follow_up.py`
   - follow-up actions
   - result summary
   - escalation
3. `workout_publication_executive.py`
   - case closure
   - assist summary
   - spotlight/recommendation glue
4. `workout_published_history.py`
   - orchestration do corredor
   - queryset base
   - montagem final do bundle

### Lente do front-end

Pela lente do `$CSS Front end architect`, o risco aqui nao e so backend.

Se o payload continuar nascendo em qualquer lugar:

1. template vira refem de nomes acidentais
2. classes e tons acabam acoplados a query
3. o front perde ownership

Guardrail:

1. quando um corredor gerar muitos labels, chips, tones ou CTAs, ele deve fechar isso em `context/presenter`, nao deixar o template adivinhar

### Lente de performance

Pela lente do `$OctoBox High Performance Architect`, o objetivo nao e "modularizar bonito".

O objetivo e:

1. preservar ou reduzir queries
2. manter prefetch e agregacoes centralizadas
3. evitar recalcular o mesmo snapshot em varios lugares
4. preparar os corredores quentes para cache ou snapshot futuro, se precisar

Estimativa de ganho esperado:

1. menos risco de N+1 acidental
2. menos duplicacao de leitura
3. mais facilidade para medir cada corredor separadamente

## A - Acoes por ondas

## Onda 0 - Inventario e baseline

### Objetivo

Congelar o comportamento antes da obra.

### Acoes

1. mapear em `operations/queries.py` quais funcoes sao:
   - leitura pura
   - serializer/context
   - CTA/copy
   - heuristica de prioridade
2. mapear em `operations/workout_published_history.py` quais funcoes sao:
   - metrics/readiness
   - follow-up/escalation
   - executive summary
   - orchestration
3. listar testes existentes que cobrem:
   - workspaces operacionais
   - board de aprovacao/publicacao do WOD
4. registrar um baseline simples de risco:
   - linhas por corredor
   - querysets centrais
   - payloads sensiveis

### Check de pronto

1. sabemos exatamente o que mover sem discutir na hora
2. sabemos o que nao tocar ainda

## Onda 1 - Extrair manager de `operations/queries.py`

### Objetivo

Atacar o trecho com melhor ROI.

### Escopo

Extrair para algo como:

1. `operations/manager_workspace_queries.py`

Conteudos alvo:

1. history events e recent history
2. focus/priority/board content
3. attach decisions de intake/link/finance
4. serializers do manager

### Regra de corte

1. se uma funcao so faz manager, ela sai
2. se uma funcao e compartilhada por varios papeis, ela pode ficar provisoriamente em `queries.py`

### Check de pronto

1. `build_manager_workspace_snapshot()` passa a orquestrar
2. os helpers de manager somem do corpo central de `queries.py`

## Onda 2 - Extrair reception de `operations/queries.py`

### Objetivo

Separar o corredor que hoje mistura leitura de fila, WhatsApp/log e hints operacionais.

### Escopo

Extrair para algo como:

1. `operations/reception_workspace_queries.py`

Conteudos alvo:

1. `_build_reception_payment_reason`
2. `_build_reception_focus_signal`
3. `_build_reception_workspace_core`
4. serializers e queue payload especificos de reception, se existirem

### Ponto de atencao de performance

Esse corte deve preservar:

1. bulk lookup dos logs de WhatsApp
2. mapa de latest finance touch
3. zero regressao para N+1

### Check de pronto

1. reception deixa de contaminar o corpo central de `queries.py`
2. o corredor de balcao fica com nome e ownership claros

## Onda 3 - Extrair owner, coach e dev de `operations/queries.py`

### Objetivo

Fechar o desinchamento do arquivo sem abrir modulo demais cedo.

### Ordem recomendada

1. owner
2. coach
3. dev

Motivo:

1. owner ainda tem mix de focus, metric cards e context
2. coach e dev sao menores e mais previsiveis depois disso

### Check de pronto

1. `operations/queries.py` fica como casca de compatibilidade ou pequeno hub compartilhado
2. cada papel tem corredor proprio

## Onda 4 - Extrair metrics/readiness do historico publicado

### Objetivo

Comecar o fatiamento do dominio pos-publicacao sem quebrar a coesao.

### Escopo

Criar:

1. `operations/workout_publication_metrics.py`

Mover:

1. `build_publication_runtime_metrics`
2. `build_publication_rm_readiness`

### Check de pronto

1. o historico publicado delega essas contas para um modulo proprio
2. a fronteira de metricas fica clara

## Onda 5 - Extrair follow-up e escalation

### Objetivo

Separar o corredor de resposta operacional do corredor de leitura bruta.

### Escopo

Criar:

1. `operations/workout_publication_follow_up.py`

Mover:

1. `_push_operational_action`
2. `_collect_relevant_follow_up_alerts`
3. `build_follow_up_result_summary`
4. `build_live_follow_up_escalation`
5. `build_publication_follow_up_actions`

### Check de pronto

1. follow-up passa a ser corredor proprio
2. `workout_published_history.py` deixa de carregar toda a estrategia de resposta no meio da leitura

## Onda 6 - Extrair executive summary e fechamento de caso

### Objetivo

Deixar a orquestracao final mais leve e previsivel.

### Escopo

Criar:

1. `operations/workout_publication_executive.py`

Mover:

1. `build_operational_memory_digest`
2. `build_executive_case_closure`
3. colas de assist summary que hoje moram no final de `build_published_workout_history()`

### Check de pronto

1. `workout_published_history.py` vira um orchestrator de dominio
2. os sumarios executivos ficam em bancada propria

## Onda 7 - Poda, compatibilidade e limpeza final

### Objetivo

Fechar a obra sem deixar pontes mortas demais.

### Acoes

1. remover imports orfaos
2. remover helpers redundantes
3. manter apenas wrappers finos se ainda houver call sites antigos
4. revisar docstrings de topo dos novos modulos

### Check de pronto

1. nenhum modulo novo existe "porque sim"
2. a arvore final explica melhor o sistema do que antes

## Guardrails tecnicos

### Arquitetura

1. nao reescrever o workspace inteiro
2. nao criar camada generica de presenter se um modulo claro resolver
3. preferir fachada antes de extracao total
4. preservar interfaces publicas enquanto o corredor ainda esta em obra

### Front/CSS

1. templates nao devem aprender regra nova por causa da refatoracao
2. `tone`, `chip`, `label` e `CTA` devem nascer em contrato claro
3. evitar classes acidentais espalhadas por queryset builder

### Performance

1. manter `select_related` e `prefetch_related` concentrados
2. nao duplicar queryset base ao fatiar modulos
3. se um helper novo for chamado dentro de loop, revisar imediatamente
4. sempre pensar em "antes e depois" de queries, mesmo sem benchmark formal

## Critério de pronto

Uma onda so esta pronta quando:

1. o comportamento continua igual
2. o arquivo principal ficou menor de verdade
3. a nova fronteira ficou mais clara de explicar
4. nao houve regressao obvia de leitura ou performance
5. o proximo corte ficou mais facil que o anterior

## O que nao fazer agora

1. microservices
2. CQRS formal
3. framework interno de payload
4. mover tudo para `facade/` por dogma
5. dividir `workout_published_history.py` em 10 arquivos de uma vez

## Prompt de execucao - Onda 1

```text
/elite prompt
Voce vai executar a Onda 1 do C.O.R.D.A. de `operations/queries.py`.

Missao:
Extrair o corredor de manager para um modulo proprio sem mudar comportamento.

Contexto obrigatorio:
- Leia `docs/architecture/octobox-architecture-model.md`
- Leia `docs/architecture/architecture-growth-plan.md`
- Leia `docs/reference/operations-wod-ownership-map.md`
- Leia `docs/plans/operations-queries-and-published-history-corda.md`

Escopo:
- Criar `operations/manager_workspace_queries.py`
- Mover para la apenas o que for ownership claro de manager
- Fazer `build_manager_workspace_snapshot()` em `operations/queries.py` virar orquestrador fino
- Preservar payload, URLs e semantica

Restrições:
- Sem arquitetura teatral
- Sem quebrar contratos de tela
- Sem piorar queries por repeticao acidental
- Use `apply_patch` para edits

Saida esperada:
1. resumo curto do corte
2. lista dos arquivos alterados
3. validacao executada
4. riscos residuais honestos
```

## Prompt de execucao - Onda 2

```text
/elite prompt
Voce vai executar a Onda 2 do C.O.R.D.A. de `operations/queries.py`.

Missao:
Extrair o corredor de reception para um modulo proprio, preservando a leitura operacional e os atalhos de balcao.

Contexto obrigatorio:
- Leia `docs/plans/operations-queries-and-published-history-corda.md`
- Revise o modulo novo de manager antes de mexer

Escopo:
- Criar `operations/reception_workspace_queries.py`
- Mover o corredor de `reception` com ownership claro
- Preservar bulk lookup de WhatsApp e mapa de latest finance touch
- Deixar `build_reception_workspace_snapshot()` mais fino

Restrições:
- Nao introduzir N+1
- Nao mudar payload de template sem necessidade
- Nao misturar concern de manager com concern de reception

Saida esperada:
1. resumo da extracao
2. comparacao antes/depois de risco arquitetural
3. validacao executada
4. pontos ainda deixados para a proxima onda
```

## Prompt de execucao - Onda 4

```text
/elite prompt
Voce vai executar a Onda 4 do C.O.R.D.A. de `operations/workout_published_history.py`.

Missao:
Extrair metrics e RM readiness para um corredor proprio sem perder coesao do dominio.

Contexto obrigatorio:
- Leia `docs/plans/operations-queries-and-published-history-corda.md`
- Revise `operations/workout_published_history.py`
- Revise testes do corredor de aprovacao/publicacao do WOD

Escopo:
- Criar `operations/workout_publication_metrics.py`
- Mover `build_publication_runtime_metrics` e `build_publication_rm_readiness`
- Manter `workout_published_history.py` como orquestrador

Restrições:
- Sem mudar comportamento
- Sem perder prefetch útil
- Sem criar modulo abstrato demais

Saida esperada:
1. resumo curto
2. arquivos alterados
3. validacao executada
4. proximos cortes naturais
```

## Prompt spec resumido desta frente

### Objetivo

Desinchar os corredores de leitura operacional com evolucao segura e testavel.

### Inputs

1. `operations/queries.py`
2. `operations/workout_published_history.py`
3. testes relacionados
4. docs arquiteturais oficiais

### Non-goals

1. redesenhar UX
2. mexer em URLs publicas
3. reescrever dominio

### Contrato de saida

Cada onda deve entregar:

1. corte unico e claro
2. validacao real
3. observacao honesta de risco residual
4. proximo passo natural

### Avaliacao

Esse CORDA esta bom se:

1. o time consegue executar onda por onda sem se perder
2. cada modulo novo nasce com ownership facil de explicar
3. a base fica mais legivel e nao mais cerimoniosa
