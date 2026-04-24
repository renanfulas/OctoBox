<!--
ARQUIVO: C.O.R.D.A. de refatoracao segura das views de workspace operacional.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- trilho de refatoracao incremental

AUTORIDADE:
- alta para a evolucao estrutural de `operations/workspace_views.py`

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md)

QUANDO USAR:
- quando a duvida for como emagrecer `operations/workspace_views.py` sem reescrever a operacao
- quando precisarmos separar view HTTP, leitura operacional, payload e mutacao
- quando a board de aprovacao do WOD estiver crescendo mais rapido do que a seguranca de manutencao

POR QUE ELE EXISTE:
- evita que a borda HTTP vire o cerebro do produto
- reduz acoplamento entre request/response, heuristica operacional e montagem de contexto
- protege a evolucao da board contra regressao silenciosa e performance acidental ruim

O QUE ESTE ARQUIVO FAZ:
1. formaliza o problema atual de concentracao em `operations/workspace_views.py`
2. define o alvo arquitetural sem rewrite
3. organiza a refatoracao por ondas pequenas e testaveis
4. registra o que nao fazer agora para evitar overengineering
5. aponta para o inventario vivo da Onda 0 em [operations-workspace-views-wave0-inventory.md](operations-workspace-views-wave0-inventory.md)
6. referencia o mapa final de ownership em [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)

PONTOS CRITICOS:
- arquivo grande sozinho nao significa gargalo de CPU
- o risco real aqui e mistura de responsabilidades, dificuldade de teste e regressao de query
- refatorar sem baseline de comportamento pode trocar bagunca visivel por bug invisivel
-->

# C.O.R.D.A. - Refatoracao segura das views de workspace operacional

## C - Contexto

O runtime atual do OctoBox ja evoluiu para um modelo melhor do que um Django solto por paginas:

1. `operations/queries.py` ja concentra leituras reutilizaveis
2. `operations/presentation.py` ja concentra contratos de page payload
3. `operations/actions.py` e `operations/action_views.py` ja mostram a tese de tirar mutacao da borda HTTP
4. `operations/facade/` ja existe como corredor oficial em partes do dominio

Mesmo assim, `operations/workspace_views.py` cresceu demais e hoje concentra funcoes demais no mesmo lugar.

Estado observado na base atual:

1. `operations/workspace_views.py` esta com 878 linhas no runtime atual observado em 2026-04-24
2. o arquivo segue misturando workspaces por papel, planner WOD, editor WOD, gestao de templates, approval/history e RM quick edit
3. o corredor de WOD puxou para dentro da mesma borda:
   - historico publicado
   - follow-up
   - memoria operacional
   - tendencias
   - checkpoint semanal
   - maturidade
   - governanca
4. a frente de templates persistentes agora tambem vive no mesmo arquivo:
   - management
   - policy update
   - duplicate/delete/toggle
   - blocos e movimentos

Em linguagem simples:

1. a porta de entrada da casa esta fazendo trabalho de recepcao, cozinha, almoxarifado e diretoria ao mesmo tempo

### Leitura arquitetural correta

Pelo modelo oficial do projeto:

1. view HTTP pertence ao `Nivel 1: acesso externo`
2. payload e leitura organizada deveriam ficar mais proximos da camada de apresentacao e leitura
3. regra e heuristica nao devem ficar espremidas na borda se precisarem crescer com seguranca

### Tese do problema

O problema principal nao e "arquivo grande deixa o servidor lento" por si so.

O problema principal e:

1. acoplamento excessivo
2. baixa previsibilidade de manutencao
3. baixa testabilidade isolada
4. risco de regressao de query e contexto
5. dificuldade de enxergar onde otimizar de verdade

## O - Objetivo

Refatorar `operations/workspace_views.py` por ondas, sem rewrite, para que:

1. as views HTTP fiquem curtas e orquestradoras
2. builders puros saiam da borda e fiquem em modulos mais apropriados
3. mutacoes relacionadas ao WOD operacional saiam da view monolitica e ganhem ownership claro
4. a board continue com o mesmo comportamento funcional
5. a refatoracao crie mais seguranca para proximas evolucoes, e nao so "beleza de codigo"

### Sucesso significa

1. `WorkoutApprovalBoardView` orquestra em vez de pensar demais
2. action views do WOD nao ficam misturadas com toda a leitura do workspace
3. conseguimos testar snapshot, leitura executiva e heuristica sem depender da view inteira
4. a performance nao piora
5. o time passa a ter corredores mais claros para continuar evoluindo

## R - Riscos

### 1. Refatorar cedo demais para uma arquitetura teatral

Se tentarmos criar 12 camadas novas agora:

1. o time perde velocidade
2. a base fica mais dificil para onboarding
3. o ganho real nao paga o custo

Traducao infantil:

1. nao vamos construir aeroporto para atravessar a rua

### 2. Trocar concentracao por espalhamento caotico

Se quebrarmos o arquivo em muitos lugares sem ownership claro:

1. a leitura piora
2. o debug fica mais lento
3. cada bug vira caça ao tesouro

### 3. Mover logica para a camada errada

Exemplos de erro:

1. query pesada em presenter
2. heuristica de negocio em template
3. mutacao sensivel em helper sem auditoria

### 4. Regressao silenciosa de payload

Se a board mudar shape sem perceber:

1. template quebra
2. leitura visual degrada
3. testes podem ficar verdes demais se cobrirem pouco contexto

### 5. Regressao de performance sem perceber

Ao mover codigo:

1. podemos duplicar queryset
2. repetir prefetch
3. perder reuso de snapshot

### 6. Querer otimizar CPU sem medir o gargalo real

Arquivo grande aumenta risco arquitetural, mas nao prova gargalo de runtime.

Se a gente atacar o alvo errado:

1. reorganiza o codigo
2. mas nao melhora a experiencia do usuario

## D - Direcao

### Tese central

Refatorar por extracao de responsabilidade, nao por reescrita.

### Regra-mestra

1. view HTTP orquestra
2. query monta leitura
3. builder puro monta payload e leitura executiva
4. mutacao vive em action view ou use case/facade

### Alvo de organizacao

Sem mexer no produto visivel primeiro, o alvo e aproximar o modulo do seguinte formato mental:

1. `operations/workspace_views.py`
   - classes HTTP de workspace
   - dispatch, permissao, contexto minimo
2. `operations/queries.py`
   - querysets, prefetch, leitura base e joins
3. `operations/presentation.py` ou modulo de apresentacao especifico
   - page payload e shape de tela
4. modulo especifico da board de WOD
   - snapshots puros
   - historico publicado
   - leitura executiva
   - resumo semanal
5. `operations/action_views.py` ou modulo de action views do WOD
   - aprovar, rejeitar, follow-up, memoria operacional, checkpoint semanal

### Direcao recomendada de extração

Para conversar com a estrutura real do repo, a refatoracao deve preferir:

1. criar poucos modulos novos e bem nomeados
2. reaproveitar `queries.py`, `presentation.py`, `actions.py` e `action_views.py`
3. evitar pacote novo se um arquivo claro resolver

### Nomeacao pragmatica recomendada

Se precisarmos abrir corredores novos, a ordem mais saudavel e:

1. `operations/workout_board_builders.py`
   - builders puros de snapshot, diff, resumo e leitura executiva
2. `operations/workout_board_history.py`
   - montagem do historico publicado, follow-up e checkpoint semanal
3. `operations/workout_action_views.py`
   - action views especificas do WOD

Observacao:

1. isso e uma direcao recomendada
2. se durante a implementacao der para resolver com 1 ou 2 arquivos novos, melhor
3. a regra e clareza com o menor numero util de modulos

### Antialvo oficial

Nao fazer agora:

1. microservices
2. CQRS formal
3. event bus novo
4. camada generica de presenter ultra-abstrata
5. "framework interno" para board

## A - Acoes por ondas

## Onda 0 - Congelar comportamento e medir o corredor

### Objetivo

Criar um baseline para refatorar sem andar no escuro.

### Acoes

1. mapear os grupos de responsabilidade atuais dentro de `operations/workspace_views.py`
2. listar quais helpers sao puros e quais tocam banco
3. revisar cobertura atual de:
   - `tests/test_coach_wod_editor.py`
   - testes de workspace e student app que dependam do WOD publicado
4. registrar os contratos minimos da board:
   - shape principal de contexto
   - filtros
   - approval flow
   - follow-up
   - checkpoint semanal

### Check de pronto

1. sabemos exatamente o que pode ser movido sem tocar em regra
2. temos testes suficientes para nao refatorar no escuro

## Onda 1 - Extrair corredor de templates para `workout_template_views.py`

### Objetivo

Tirar de `workspace_views.py` o corredor mais coeso e de maior write density sem mexer no contrato de URLs.

### Escopo direto

1. `WorkoutTemplateManagementView`
2. `WorkoutApprovalPolicyUpdateView`
3. `WorkoutTemplateDuplicateView`
4. `WorkoutTemplateDeleteView`
5. `WorkoutTemplateToggleActiveView`
6. `WorkoutTemplateToggleFeaturedView`
7. `WorkoutTemplateUpdateMetadataView`
8. `WorkoutTemplateUpdateBlockView`
9. `WorkoutTemplateCreateBlockView`
10. `WorkoutTemplateDeleteBlockView`
11. `WorkoutTemplateMoveBlockView`
12. `WorkoutTemplateUpdateMovementView`
13. `WorkoutTemplateCreateMovementView`
14. `WorkoutTemplateDeleteMovementView`
15. `WorkoutTemplateMoveMovementView`

### Direcao

Mover para `operations/workout_template_views.py`, mantendo:

1. os mesmos nomes de rota
2. as mesmas permissoes
3. a mesma casca HTTP
4. o mesmo fallback de degradacao quando as tabelas de template nao existirem no banco

### Check de pronto

1. `urls.py` passa a importar as views de template do novo modulo
2. `workspace_views.py` perde o corredor de templates inteiro
3. testes do editor/planner/templates continuam verdes

## Onda 2 - Extrair planner para `workout_planner_views.py`

### Objetivo

Separar o cockpit do WOD para um modulo proprio, preservando a navegacao e a telemetria do picker.

### Escopo direto

1. `WorkoutPlannerView`
2. `WorkoutPlannerTemplatePickerTelemetryView`
3. `WorkoutPlannerApplyTrustedTemplateView`
4. `WorkoutPlannerDuplicatePreviousSlotView`

### Direcao

Mover o corredor inteiro para `operations/workout_planner_views.py`, sem reabsorver contexto ou builder puro para dentro da view.

### Check de pronto

1. planner deixa de conviver com templates e workspaces por papel no mesmo arquivo
2. rotas e comportamento ficam identicos
3. smoke tests de planner permanecem verdes

## Onda 3 - Extrair builders puros e corredores densos da board

### Objetivo

Separar a leitura operacional mais densa do WOD em um corredor HTTP proprio.

### Escopo direto

1. `WorkoutApprovalBoardView`
2. `WorkoutPublicationHistoryView`
3. `OperationsExecutiveSummaryView`
4. `WorkoutStudentRmQuickEditView`

### Direcao

Mover para `operations/workout_board_views.py`, mantendo o corredor WOD coeso:

1. board
2. history
3. executive summary
4. quick edit de RM

### Regra

Leitura operacional deve ficar perto de:

1. contexto da board
2. contexto de historico
3. resumo executivo
4. quick edit do corredor

### Check de pronto

1. `workspace_views.py` para de concentrar board e historico do WOD
2. `urls.py` continua estavel
3. approval, history e quick edit continuam identicos por fora

## Onda 4 - Extrair corredor do editor

### Objetivo

Separar o editor do coach/owner e o preview de prescricao do arquivo geral de workspace.

### Escopo direto

1. `WorkoutEditorHomeView`
2. `CoachSessionWorkoutEditorView`
3. `WorkoutPrescriptionPreviewView`

### Direcao

Mover para `operations/workout_editor_views.py`, preservando:

1. contract do editor
2. preview backend
3. comportamento do redirect `workout-editor-home`

### Check de pronto

1. o corredor do editor sai de `workspace_views.py`
2. o editor continua verde nos testes
3. o arquivo principal vira casca de workspaces por papel

## Onda 5 - Encurtar as workspace views restantes

### Objetivo

Fazer o arquivo principal sobrar apenas para workspaces por papel e superficies realmente compartilhadas.

### Acoes

1. revisar helpers compartilhados restantes
2. manter no arquivo principal apenas:
   - Owner/Dev/Manager/Coach/Reception workspaces
   - event streams
   - placeholders gerais, se ainda fizer sentido

### Check de pronto

1. uma pessoa nova entende o arquivo principal em poucos minutos
2. cada corredor WOD tem ownership proprio
3. o arquivo principal deixa de ser gargalo cognitivo

## Onda 6 - Revisao de query, payload e docs de ownership

### Objetivo

Fechar a refatoracao com medicao e documentacao alinhadas ao runtime real.

### Acoes

1. revisar duplicacao de queryset e payload depois dos splits
2. conferir `select_related` e `prefetch_related` nos corredores novos
1. atualizar `docs/reference/reading-guide.md` se os pontos de entrada mudarem
2. atualizar planos ligados ao WOD quando os ownerships mudarem
3. deixar explicito onde mora:
   - leitura da board
   - leitura do planner
   - leitura do editor
   - mutacao da board
   - checkpoint semanal
   - aprendizado operacional

### Check de pronto

1. o mapa da cidade bate com a rua real

## Ordem recomendada de execucao

Se formos atacar isso agora, a melhor ordem e:

1. Onda 0
2. Onda 1
3. Onda 2
4. Onda 3
5. pausa curta para validar
6. Onda 4
7. Onda 5
8. Onda 6

## Guardrails finais

### O que manter

1. evolucao incremental
2. vocabulario oficial do OctoBox
3. borda HTTP curta
4. auditoria intacta
5. testes como rede de protecao

### O que evitar

1. refatorar por vaidade
2. abrir modulo demais sem necessidade
3. abstrair cedo demais
4. confundir organizacao de codigo com otimizacao comprovada

## Resumo executivo

Hoje `operations/workspace_views.py` ja esta grande o suficiente para merecer emagrecimento estrutural.

Mas a jogada certa nao e demolir a casa.

E:

1. tirar a cozinha da recepcao
2. separar o caixa da sala do gerente
3. deixar a porta de entrada so como porta

Traducao tecnica:

1. view HTTP deve orquestrar
2. board do WOD deve ter corredor proprio
3. mutacao deve sair da leitura monolitica
4. a refatoracao deve ser guiada por testes e por ownership, nao por ansiedade arquitetural

## Estado apos as ondas executadas

Ao final das ondas estruturais executadas nesta trilha, o corredor ficou assim:

1. `operations/workspace_views.py`
   - workspaces por papel
   - event streams
   - placeholders e superficies gerais
2. `operations/workout_template_views.py`
   - management e mutacoes de templates persistentes
3. `operations/workout_planner_views.py`
   - planner, picker telemetry e acoes do cockpit
4. `operations/workout_board_views.py`
   - board, history, executive summary e quick edit de RM
5. `operations/workout_editor_views.py`
   - editor do coach/owner e preview backend de prescricao
6. `operations/workout_action_views.py`
   - mutacoes reais da board
7. `operations/workout_approval_board_context.py`
   - coordenacao do contexto da board
8. `operations/workout_support.py`
   - suporte compartilhado de snapshot, revisao, auditoria e review snapshot

Medida objetiva da trilha:

1. `operations/workspace_views.py` saiu de 878 linhas no baseline observado em 2026-04-24
2. e terminou em 231 linhas apos as ondas 1 a 4
3. os corredores novos ficaram assim:
   - `operations/workout_template_views.py` -> 388 linhas
   - `operations/workout_planner_views.py` -> 134 linhas
   - `operations/workout_board_views.py` -> 123 linhas
   - `operations/workout_editor_views.py` -> 103 linhas

Leitura correta:

1. a view principal deixou de ser o cerebro do corredor de WOD
2. agora ela e a casca de entrada
3. os corredores internos passaram a ter ownership mais claro
4. o split foi feito por capacidade, nao por abstracao generica
