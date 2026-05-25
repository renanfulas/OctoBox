<!--
ARQUIVO: inventario tecnico da Onda 0 para refatoracao de `operations/workspace_views.py`.

TIPO DE DOCUMENTO:
- inventario arquitetural
- mapa de ownership e cortes recomendados

AUTORIDADE:
- alta para iniciar a refatoracao da view operacional por ondas

DOCUMENTOS PAIS:
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md)

QUANDO USAR:
- antes de mover qualquer bloco relevante de `operations/workspace_views.py`
- quando a duvida for o que e puro, o que toca banco e o que e mutacao
- quando precisarmos decidir a primeira extracao com menor risco

POR QUE ELE EXISTE:
- evita refatoracao por intuicao
- cria um mapa de responsabilidade real do arquivo
- protege a ordem de extracao contra espalhamento caotico

O QUE ESTE ARQUIVO FAZ:
1. fotografa o estado atual do arquivo
2. classifica responsabilidades por corredor
3. identifica os principais acoplamentos externos
4. recomenda os primeiros cortes seguros
-->

# Onda 0 - Inventario tecnico de `operations/workspace_views.py`

## Foto atual

Estado observado no runtime atual:

1. `operations/workspace_views.py` esta com 2535 linhas
2. `student_app/views.py` esta com 385 linhas
3. a maior densidade de complexidade esta concentrada no corredor do WOD operacional e da board de aprovacao

Leitura curta:

1. o arquivo deixou de ser "um conjunto de views"
2. ele virou uma mistura de view HTTP, presenter, query assembler, workflow de leitura executiva e action views

## Mapa de responsabilidade por faixa

### Faixa 1 - Casca de workspace por papel

Responsabilidade:

1. montar contexto para owner
2. montar contexto para manager
3. montar contexto para coach
4. montar contexto para dev
5. montar contexto para recepcao

Pontos principais:

1. `_attach_operation_workspace_payload`
2. `_build_reception_workspace_payload`
3. `_build_manager_workspace_payload`
4. `OwnerWorkspaceView`
5. `ManagerWorkspaceView`
6. `CoachWorkspaceView`
7. `DevWorkspaceView`
8. `ReceptionWorkspaceView`

Leitura:

1. esta faixa ainda conversa com o papel do arquivo
2. ela esta menos problematica do que a board de WOD

## Faixa 2 - Biblioteca escondida de builders puros do WOD

Responsabilidade:

1. serializacao de snapshot
2. normalizacao de blocos
3. montagem de preview do aluno
4. diff estrutural do treino
5. diff de experiencia do aluno
6. leitura assistida de decisao
7. sinais executivos e maturidade semanal

Pontos principais:

1. `_serialize_workout_snapshot`
2. `_normalize_snapshot_blocks`
3. `_build_snapshot_presentation`
4. `_build_student_preview_payload`
5. `_build_student_preview_diff`
6. `_build_workout_decision_assist`
7. `_build_workout_diff_snapshot`
8. `_build_workout_review_snapshot`
9. `_build_operational_memory_patterns`
10. `_build_operational_leverage_summary`
11. `_build_operational_leverage_trends`
12. `_build_operational_management_alerts`
13. `_build_management_alert_priority`
14. `_build_management_recommendations`
15. `_build_weekly_executive_summary`
16. `_build_weekly_checkpoint_history`
17. `_build_weekly_checkpoint_rhythm`
18. `_build_weekly_checkpoint_maturity`
19. `_build_weekly_governance_action`

Leitura:

1. esse e o corredor mais claro para a primeira extracao
2. boa parte aqui e calculo puro ou quase puro
3. ele ja se comporta como modulo proprio, so que ainda mora dentro da view

Analogia infantil:

1. isso e como encontrar uma biblioteca inteira escondida dentro do hall de entrada da escola

## Faixa 3 - Montagem densa do historico publicado

Responsabilidade:

1. ler revisoes publicadas
2. calcular runtime da aula
3. cruzar follow-up
4. montar closure executivo
5. montar spotlight de alertas
6. montar resumo semanal
7. montar aprendizado operacional

Ponto principal:

1. `_build_published_workout_history`

Leitura:

1. esse e o bloco mais pesado e mais sensivel da board
2. ele mistura query, regra, agregacao, heuristica e shape final
3. e o principal candidato a virar um corredor proprio logo depois dos builders puros

Risco:

1. qualquer extracao aqui sem teste suficiente pode gerar regressao silenciosa de payload ou query

## Faixa 4 - Editor do WOD do coach

Responsabilidade:

1. criar rascunho
2. editar cabecalho
3. adicionar bloco
4. remover bloco
5. editar bloco
6. adicionar movimento
7. remover movimento
8. editar movimento
9. enviar para aprovacao
10. duplicar WOD

Ponto principal:

1. `CoachSessionWorkoutEditorView`

Leitura:

1. esta classe sozinha ja e um mini-controller transacional
2. ela concentra muitos intents no mesmo `post`
3. porem os fluxos estao coesos entre si e pertencem ao dominio do editor do coach

Recomendacao:

1. nao e o primeiro corte mais barato
2. primeiro vale separar a board de aprovacao e a biblioteca escondida
3. depois podemos decidir se esse editor merece action views ou facade propria

## Faixa 5 - Board de aprovacao do WOD

Responsabilidade:

1. montar fila pendente
2. filtrar por coach, sensibilidade e dia
3. calcular review snapshot
4. montar checkpoint semanal
5. montar historico publicado
6. expor assistencia executiva

Ponto principal:

1. `WorkoutApprovalBoardView`

Leitura:

1. esta classe hoje e a maior prova de concentracao arquitetural
2. ela ainda funciona, mas ja esta pesada para continuar crescendo com seguranca

Recomendacao:

1. a view deve virar casca fina
2. a maior parte do trabalho dela deve ser delegada para builders/coordinators externos

## Faixa 6 - Mutacoes operacionais do WOD

Responsabilidade:

1. aprovar WOD
2. rejeitar WOD
3. registrar follow-up
4. registrar memoria operacional
5. registrar checkpoint semanal

Pontos principais:

1. `WorkoutApprovalActionView`
2. `WorkoutFollowUpActionView`
3. `WorkoutOperationalMemoryCreateView`
4. `WorkoutWeeklyCheckpointUpdateView`

Leitura:

1. essas classes sao mutacoes reais
2. elas ja nao combinam mais com a ideia de um arquivo de "workspace view" apenas
3. pertencem mais naturalmente a um corredor de `action_views`

Recomendacao:

1. esse e o terceiro corte natural, depois da extracao dos builders e do historico publicado

## Classificacao por tipo de responsabilidade

### Grupo A - Puro ou quase puro

Sinais:

1. nao dependem de `request`
2. recebem dados e devolvem estrutura
3. tem alto potencial de teste unitario isolado

Entram aqui:

1. `_build_student_preview_payload`
2. `_build_student_preview_diff`
3. `_build_workout_decision_assist`
4. `_build_workout_diff_snapshot`
5. `_build_operational_memory_patterns`
6. `_build_operational_leverage_summary`
7. `_build_operational_leverage_trends`
8. `_build_operational_management_alerts`
9. `_build_management_alert_priority`
10. `_build_management_recommendations`
11. `_build_weekly_executive_summary`
12. `_build_weekly_checkpoint_rhythm`
13. `_build_weekly_checkpoint_maturity`
14. `_build_weekly_governance_action`

### Grupo B - Leitura com banco e agregacao

Sinais:

1. usam queryset
2. cruzam revisoes, follow-up e checkpoint
3. montam leitura rica para tela

Entram aqui:

1. `_build_weekly_checkpoint_history`
2. `_build_published_workout_history`
3. `WorkoutApprovalBoardView.get_context_data`
4. partes de `CoachSessionWorkoutEditorView.dispatch` e `_build_context`

### Grupo C - Mutacao com auditoria

Sinais:

1. mudam estado real
2. escrevem auditoria
3. dependem de messages e redirect

Entram aqui:

1. `_create_workout_revision`
2. `_record_workout_audit`
3. `CoachSessionWorkoutEditorView.post`
4. `WorkoutApprovalActionView.post`
5. `WorkoutFollowUpActionView.post`
6. `WorkoutOperationalMemoryCreateView.post`
7. `WorkoutWeeklyCheckpointUpdateView.post`

## Acoplamentos externos importantes

### URLs

Hoje `operations/urls.py` importa de `workspace_views.py`:

1. `CoachSessionWorkoutEditorView`
2. `WorkoutApprovalBoardView`
3. `WorkoutApprovalActionView`
4. `WorkoutFollowUpActionView`
5. `WorkoutOperationalMemoryCreateView`
6. `WorkoutWeeklyCheckpointUpdateView`

Conclusao:

1. ao mover action views, o impacto em URL sera pequeno e controlado
2. o contrato publico das rotas pode continuar identico

### Forms

Hoje `operations/forms.py` ja esta bem posicionado como borda de validacao para:

1. aprovacao
2. rejeicao
3. follow-up
4. memoria operacional
5. checkpoint semanal
6. editor do coach

Conclusao:

1. forms nao sao o gargalo
2. eles podem permanecer onde estao durante a refatoracao

### Testes

Hoje `tests/test_coach_wod_editor.py` tem 1186 linhas e cobre:

1. editor do coach
2. board de aprovacao
3. checkpoint semanal
4. follow-up
5. memoria operacional
6. historico publicado

Conclusao:

1. esse arquivo e a principal rede de seguranca da refatoracao
2. antes de cortes maiores, vale no futuro separar a suite por corredor, mas isso nao e pre-requisito imediato

## Ordem de extracao recomendada

### Corte 1 - Mais barato e mais seguro

Extrair a biblioteca escondida de builders puros.

Motivo:

1. alto ganho de clareza
2. baixo risco de side effect
3. melhora testabilidade rapidamente

### Corte 2 - Mais valioso

Extrair `_build_published_workout_history` e helpers adjacentes para corredor proprio.

Motivo:

1. ali mora a maior densidade da board
2. ali fica mais facil revisar query e payload depois

### Corte 3 - Mais semantico

Mover action views do WOD para `action_views` ou modulo proprio.

Motivo:

1. separa leitura de mutacao
2. alinha melhor com a tese atual do repo

### Corte 4 - Casca fina da board

Enxugar `WorkoutApprovalBoardView`.

Motivo:

1. depois dos cortes 1, 2 e 3 ela fica pronta para virar orquestradora

## O que nao cortar primeiro

### Nao comecar por `CoachSessionWorkoutEditorView`

Motivo:

1. embora grande, ela ainda e um corredor relativamente coeso
2. a board de aprovacao esta mais densa e traz mais risco estrutural hoje

### Nao criar framework novo de presenters

Motivo:

1. o repo ja tem `operations/presentation.py`
2. o objetivo agora e ownership claro, nao abstrair por esporte

## Decisao executiva da Onda 0

O melhor proximo passo tecnico nao e "otimizar performance" no escuro.

E:

1. extrair primeiro os builders puros do corredor do WOD
2. em seguida extrair o historico publicado
3. depois tirar as mutacoes do WOD de `workspace_views.py`

Traducao infantil:

1. primeiro tiramos os livros da recepcao
2. depois tiramos o arquivo morto
3. por fim tiramos o caixa

So depois a recepcao volta a parecer recepcao.

## Fechamento posterior da trilha

As ondas seguintes fecharam exatamente esse corredor:

1. os builders puros sairam para `operations/workout_board_builders.py`
2. o historico publicado saiu para `operations/workout_published_history.py`
3. as mutacoes foram para `operations/workout_action_views.py`
4. a board ganhou coordenacao propria em `operations/workout_approval_board_context.py`
5. o suporte compartilhado foi para `operations/workout_support.py`

Para a planta final do ownership, leia:

1. [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)
