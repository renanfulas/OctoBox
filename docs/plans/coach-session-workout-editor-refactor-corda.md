<!--
ARQUIVO: C.O.R.D.A. da refatoracao segura do editor de WOD do coach.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- trilho incremental de refatoracao
- contrato de execucao por ondas

AUTORIDADE:
- alta para a evolucao estrutural de `CoachSessionWorkoutEditorView`

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando a duvida for como emagrecer o editor de WOD do coach sem quebrar o fluxo real
- quando precisarmos separar `policy -> action -> query -> presenter -> recommendation` no corredor de treino
- quando a tela do coach estiver crescendo mais rapido do que a seguranca de manutencao

POR QUE ELE EXISTE:
- evita que `CoachSessionWorkoutEditorView` continue acumulando HTTP, mutacao, leitura e montagem de UI no mesmo lugar
- protege a performance do editor e do preview de RM durante a refatoracao
- preserva a superficie visual do coach sem virar obra aparente na fachada
- transforma a execucao em uma frente reproduzivel, com criterio de pronto e verificacao

O QUE ESTE ARQUIVO FAZ:
1. formaliza o problema atual do editor de WOD do coach
2. define o alvo arquitetural mais seguro para o proximo corte
3. organiza a execucao por ondas pequenas, testaveis e reversiveis
4. integra arquitetura, performance, front-end e prompting no mesmo trilho

PONTOS CRITICOS:
- o problema aqui nao e so tamanho de arquivo; e mistura de responsabilidade
- refatoracao bonita que piora query count ou latencia falhou
- UI do coach precisa continuar estavel enquanto a obra acontece
- nao devemos criar recomendacao teatral se ela ainda nao muda a experiencia real
-->

# C.O.R.D.A. - Refatoracao segura do editor de WOD do coach

## C - Contexto

O corredor de WOD em `operations` ja avancou bem na separacao de ownership.

Hoje a base ja possui:

1. `operations/workout_board_builders.py` para leitura executiva e builders puros da board
2. `operations/workout_published_history.py` para historico publicado e pos-publicacao
3. `operations/workout_action_views.py` para mutacoes reais da board de aprovacao
4. `operations/workout_support.py` como caixa de ferramentas compartilhada
5. `operations/workout_approval_board_context.py` para contexto da board
6. [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md) como mapa oficial do corredor

Mesmo com essa evolucao, ainda existe um ponto de concentracao importante:

1. `CoachSessionWorkoutEditorView` em [../../operations/workspace_views.py](../../operations/workspace_views.py)

Hoje esse editor concentra ao mesmo tempo:

1. leitura da `ClassSession`
2. criacao lazy do `SessionWorkout`
3. montagem de contexto da tela
4. preview de RM por aluno
5. construcao do page payload
6. varios `intent` no `post()`
7. mutacoes de workout, block e movement
8. submit para aprovacao
9. duplicacao de WOD
10. auditoria e revisoes

Em linguagem simples:

1. a mesma sala ainda esta servindo como recepcao, cozinha, estoque e caixa

### Leitura arquitetural correta

Pelo modelo oficial do OctoBox:

1. a view HTTP pertence ao nivel de acesso externo
2. a regra mutavel deve sair da borda quando crescer
3. leitura pesada e composicao de UI nao devem ficar misturadas com mutacao
4. a fachada visivel do coach precisa continuar limpa, mesmo com a obra lateral

### Leitura de performance correta

Pela lente de performance:

1. o preview de RM e o contexto do editor sao os pontos com maior risco de custo escondido
2. o gargalo mais provavel nao e "Python demais", e sim query, prefetch e payload compostos sem ownership claro
3. refatorar com perda de `select_related`, `prefetch_related` ou reuso de snapshot seria regressao disfarçada

### Leitura de front-end correta

Pela lente de front-end:

1. a tela do coach e uma superficie operacional de uso frequente
2. a refatoracao nao deve espalhar logica no template
3. o HTML deve continuar previsivel para CSS, mensagens e payloads
4. se houver mudanca de markup, ela deve nascer de contrato claro e nao de improviso

## O - Objetivo

Refatorar `CoachSessionWorkoutEditorView` para uma arquitetura por capacidade, mantendo o comportamento e a experiencia atual do coach.

### Sucesso significa

1. a view HTTP fica curta e orquestradora
2. o `post()` vira dispatcher por `intent`
3. mutacoes de WOD saem para actions ou workflows dedicados
4. leitura do editor e preview de RM saem para queries ou snapshots claros
5. apresentacao da tela e payload ficam centralizados em presenter dedicado
6. a tela continua funcional, performatica e previsivel
7. a base fica pronta para futuras recomendacoes operacionais de RM sem misturar isso com a edicao do WOD

### Nao e objetivo desta frente

1. redesenhar a UX inteira do editor
2. reescrever templates sem necessidade
3. criar framework interno de componentes
4. introduzir CQRS formal ou event mesh novo
5. adicionar recomendacoes de RM apenas para justificar nova camada

## R - Riscos

### 1. Risco de arquitetura teatral

Se criarmos muitas camadas novas sem ganho real:

1. o time perde velocidade
2. a leitura fica mais cerimonial
3. a manutencao fica mais cara sem retorno

### 2. Risco de quebrar o fluxo do coach

Se o editor perder previsibilidade:

1. o coach trava no dia a dia
2. submit, duplicacao ou edicao inline podem falhar silenciosamente
3. o ganho estrutural vira perda operacional

### 3. Risco de regressao de performance

Se movermos a leitura do preview de RM do jeito errado:

1. podemos duplicar queryset
2. criar N+1
3. aumentar latencia percebida na tela do coach

### 4. Risco de vazamento visual

Se a refatoracao mexer no template sem contrato:

1. classes CSS podem perder alvo
2. mensagens podem sair do lugar
3. a fachada pode parecer remendada mesmo com backend mais bonito

### 5. Risco de duplicar regra de mutacao

Se salvar block, movement e submit forem separados sem ownership claro:

1. reset de status pode divergir
2. auditoria pode ficar inconsistente
3. `version` e revisoes podem subir errados

### 6. Risco de forcar recommendation cedo demais

O corredor ja tem materia-prima para recomendacao de RM, mas isso so deve subir para uma camada propria quando:

1. alterar decisao real do coach
2. tiver contrato claro de output
3. nao poluir o editor com inteligencia ornamental

## D - Direcao

### Tese central

Aplicar ao editor do coach o mesmo modelo que ja funcionou em `student_identity/staff_views.py`:

1. policy clara
2. action por capacidade
3. query para leitura pesada
4. presenter para payload e leitura de UI
5. recommendation apenas onde houver ganho operacional real

### Estrutura-alvo recomendada

```text
operations/
  workspace_views.py
  workout_editor_actions.py
  workout_editor_queries.py
  workout_editor_presenters.py
  workout_editor_dispatch.py
  workout_support.py
```

Observacao:

1. `workout_editor_dispatch.py` e opcional
2. se o dispatcher couber dentro de `workspace_views.py` com clareza, melhor manter mais curto
3. a prioridade e ownership real, nao quantidade de arquivos

### Ownership recomendado

#### `workspace_views.py`

Responsavel por:

1. `dispatch`
2. permissao
3. wiring de request/response
4. composicao final de contexto

Nao deveria concentrar:

1. mutacao detalhada por `intent`
2. preview pesado de RM
3. payload detalhado de UI

#### `workout_editor_actions.py`

Responsavel por:

1. `save_workout`
2. `add_block`
3. `update_block`
4. `delete_block`
5. `add_movement`
6. `update_movement`
7. `delete_movement`
8. `submit_for_approval`
9. `duplicate_workout`

Contrato:

1. mutacao com auditoria
2. reset de status quando necessario
3. atualizacao de `version`
4. redirects e mensagens apenas se a action for de camada HTTP

#### `workout_editor_queries.py`

Responsavel por:

1. snapshot da sessao
2. duplicate sessions elegiveis
3. preview de RM
4. leituras auxiliares do editor

Contrato:

1. concentrar `select_related` e `prefetch_related`
2. evitar recomposicao de query dentro da view
3. produzir leitura previsivel e reutilizavel

#### `workout_editor_presenters.py`

Responsavel por:

1. page payload do editor
2. cards do preview de RM
3. labels de cobertura, range e estado
4. shape consumido pelo template

Contrato:

1. sem query
2. sem redirect
3. sem mutacao

#### `recommendation`

Nao abrir agora por padrao.

Abrir apenas se:

1. o preview de RM passar a gerar proxima melhor acao
2. essa acao mudar o comportamento operacional do coach
3. o output puder ser testado isoladamente

### Direcao de performance

1. manter ou melhorar prefetch da `ClassSession`
2. centralizar leitura de RM em query dedicada
3. evitar loop que consulta RM aluno por aluno sem snapshot unico
4. medir antes/depois em query count quando possivel
5. tratar payload do editor como asset quente: curto, composto e previsivel

Meta qualitativa:

1. nenhuma regressao visivel na abertura da tela do coach

### Direcao de front-end

1. preservar `template_name` e fluxo visual do editor
2. manter a tela funcional em desktop e mobile operacional
3. evitar empurrar logica para template
4. qualquer mudanca de markup deve respeitar seletor existente ou explicitar migracao de CSS
5. se houver refino visual, ele entra depois da separacao estrutural, nao durante

## A - Acoes por ondas

## Onda 0 - Inventario e baseline

### Objetivo

Congelar o comportamento atual antes de abrir o editor.

### Acoes

1. mapear todos os `intent` atuais do `post()`
2. mapear os pontos que mutam `status`, `version`, revisoes e auditoria
3. registrar a leitura atual do preview de RM
4. validar testes existentes do corredor de WOD e do editor
5. registrar shape minimo de contexto entregue ao template

### Check de pronto

1. sabemos o que e leitura, o que e mutacao e o que e apresentacao
2. sabemos o que nao pode quebrar durante a obra

## Onda 1 - Extrair dispatcher do `post()`

### Objetivo

Deixar a `post()` curta e previsivel.

### Acoes

1. criar mapa de `intent -> handler`
2. mover a escolha de rota interna para dispatcher explicito
3. manter os mesmos `intent` do formulario

### Check de pronto

1. a view vira casca de entrada
2. o fluxo continua identico para o coach

## Onda 2 - Extrair actions por capacidade

### Objetivo

Separar mutacao real da borda HTTP.

### Acoes

1. mover actions de workout
2. mover actions de block
3. mover actions de movement
4. mover submit e duplicacao
5. centralizar o contrato de reset de status e bump de `version`

### Check de pronto

1. mutacao para de morar na view monolitica
2. auditoria e revisoes continuam identicas

## Onda 3 - Extrair queries do editor

### Objetivo

Separar leitura pesada e snapshot do editor.

### Acoes

1. mover carregamento da sessao com `select_related/prefetch_related`
2. mover construcao de duplicate sessions
3. mover leitura do preview de RM
4. consolidar leitura reutilizavel do editor

### Check de pronto

1. a view para de conhecer query detalhada
2. o preview de RM fica mensuravel e otimizavel

## Onda 4 - Extrair presenter do editor

### Objetivo

Separar payload e leitura de UI.

### Acoes

1. mover page payload do editor
2. mover labels do preview de RM
3. manter contrato consumido pelo template

### Check de pronto

1. a view nao monta mais dicionario visual grande
2. o template continua estavel

## Onda 5 - Reavaliar recommendation de RM

### Objetivo

Decidir com evidencia se vale criar camada de recomendacao agora.

### Perguntas-guia

1. o preview ja sugere acao real do coach?
2. existe fila operacional clara derivada do RM?
3. o ganho supera o custo de uma nova camada?

### Decisao recomendada

1. so abrir `recommendation` se houver acao operacional concreta
2. se ainda for apenas leitura assistida, manter no presenter

### Check de pronto

1. evitamos camada vazia
2. recommendation nasce apenas quando muda o jogo

## Onda 6 - Performance pass

### Objetivo

Conferir se a organizacao manteve ou melhorou o runtime.

### Acoes

1. revisar query count do editor
2. revisar prefetch de RM
3. procurar loops redundantes
4. revisar payload final

### Check de pronto

1. nenhum N+1 novo
2. nenhuma regressao visivel de latencia

## Onda 7 - CSS e template review

### Objetivo

Garantir que a obra estrutural nao vazou para a fachada.

### Acoes

1. validar markup final do editor
2. confirmar que CSS continua com ownership claro
3. revisar se alguma logica escorregou para template

### Check de pronto

1. UI continua limpa
2. CSS nao ganhou remendo desnecessario

## Prompt Overlay da frente

Esta frente combina quatro lentes:

1. `software-architecture-chief` para decidir o menor corte com maior alavanca
2. `OctoBox High Performance Architect` para proteger query, snapshot e latencia
3. `CSS Front end architect` para preservar a fachada do editor do coach
4. `prompt-engineer` para transformar a frente em contrato executavel

## Prompt Spec da frente

### Objective

Refatorar `CoachSessionWorkoutEditorView` por capacidades, preservando comportamento, UX e performance do editor do coach.

### Target model

Agente de implementacao com acesso ao codigo local e capacidade de editar, testar e validar incrementalmente.

### Inputs

1. runtime atual do editor em `operations/workspace_views.py`
2. docs canonicos do corredor de WOD
3. este C.O.R.D.A.

### Assumptions

1. a UX atual do coach deve ser preservada
2. a tela ainda e superficie viva de operacao, nao prototipo
3. recomendacao de RM so entra se gerar proxima melhor acao real

### Non-goals

1. redesenho total de interface
2. camada nova sem ownership real
3. mudanca de fluxo de aprovacao fora do contrato atual

### Constraints

1. manter os mesmos `intent` do `post()` ate aprovacao explicita
2. nao piorar query count ou latencia de forma perceptivel
3. nao espalhar logica em template
4. preservar contratos de auditoria, revisao e `version`

### Output contract

Cada onda deve entregar:

1. codigo alterado
2. contrato preservado
3. risco principal da onda
4. validacao executada
5. debito tecnico evitado ou criado

### Evaluation

O plano so e bem executado se:

1. a view ficar mais curta
2. o `post()` virar dispatcher claro
3. mutacao, leitura e apresentacao tiverem ownership proprio
4. a tela do coach continuar estavel
5. a performance nao piorar

## Prompt operacional reutilizavel

```md
Voce esta executando a frente `coach-session-workout-editor-refactor-corda`.

Objetivo:
Refatorar `CoachSessionWorkoutEditorView` por capacidades, preservando comportamento, UX e performance.

Contexto:
- O projeto segue a tese de modular monolith do OctoBox.
- A borda HTTP deve orquestrar, nao concentrar dominio.
- O corredor de WOD ja possui ownership separado para board, historico e action views.
- Esta execucao deve seguir o C.O.R.D.A. `docs/plans/coach-session-workout-editor-refactor-corda.md`.

Escopo desta execucao:
- [descreva aqui a onda atual]

Constraints:
- nao reescrever a UX do coach
- manter os mesmos `intent` do `post()` sem aprovacao explicita
- nao piorar query count ou latencia de forma perceptivel
- nao empurrar logica para o template
- preservar auditoria, revisoes e `version`

Entrega obrigatoria:
1. mudancas de codigo
2. risco principal da onda
3. validacao executada
4. debito tecnico evitado ou criado
5. observacoes sobre recommendation de RM: ainda nao, ou agora sim, com motivo
```

## Criterio final de sucesso

Ao final desta frente:

1. `CoachSessionWorkoutEditorView` deixa de ser um centro monolitico
2. `post()` vira dispatcher curto
3. mutacao, leitura e apresentacao do editor passam a ter ownership claro
4. o preview de RM fica mais facil de medir e otimizar
5. a superficie visual do coach continua limpa e previsivel
6. a base fica pronta para recomendacao operacional real sem misturar isso com a edicao do WOD
