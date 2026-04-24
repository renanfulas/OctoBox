<!--
ARQUIVO: mapa de ownership do corredor de WOD em operations.

TIPO DE DOCUMENTO:
- referencia tecnica de ownership
- mapa de leitura por responsabilidade

AUTORIDADE:
- alta para localizar a casa certa do fluxo de WOD operacional

DOCUMENTOS PAIS:
- [../plans/operations-workspace-views-refactor-corda.md](../plans/operations-workspace-views-refactor-corda.md)
- [../plans/coach-wod-approval-corda.md](../plans/coach-wod-approval-corda.md)
- [../plans/wod-test-ownership-split-corda.md](../plans/wod-test-ownership-split-corda.md)
- [wod-test-suite-ownership.md](wod-test-suite-ownership.md)
- [reading-guide.md](reading-guide.md)

QUANDO USAR:
- quando a duvida for onde mexer no fluxo de WOD do coach, aprovacao, historico publicado ou follow-up
- quando surgir bug no corredor de treino operacional
- quando um PR tocar o dominio de WOD e precisarmos saber ownership rapido

POR QUE ELE EXISTE:
- evita voltar a concentrar responsabilidade em `operations/workspace_views.py`
- reduz busca cega depois da refatoracao por ondas
- deixa explicito quem e o dono tecnico de cada parte do fluxo

O QUE ESTE ARQUIVO FAZ:
1. mapeia os modulos do corredor de WOD
2. separa leitura, mutacao, suporte e contexto
3. explica por onde abrir primeiro em cada tipo de problema
4. aponta para o plano de split da suite de testes quando a duvida for coverage ownership
-->

# Ownership do corredor de WOD em `operations`

## Tese curta

Hoje o fluxo de WOD em `operations` nao mora mais em um arquivo monolitico.

Ele foi separado em corredores diferentes:

1. casca de workspace por papel
2. templates persistentes
3. planner
4. board e historico
5. editor
6. mutacoes reais
7. suporte compartilhado

Em linguagem simples:

1. a cozinha, o caixa, a sala do mapa e a sala do professor nao dividem mais o mesmo balcao

## Mapa rapido

### 1. Casca HTTP de workspace

Arquivo:

1. [operations/workspace_views.py](../../operations/workspace_views.py)

Ownership:

1. telas operacionais por papel
2. event streams
3. placeholders e superficies gerais

Abra primeiro aqui quando:

1. a rota da tela quebrou
2. o contexto base do workspace sumiu
3. um workspace por papel falhou no fluxo HTTP

Nao deveria concentrar:

1. planner
2. editor
3. board e historico
4. mutacoes do WOD

### 2. Corredor de templates persistentes

Arquivo:

1. [operations/workout_template_views.py](../../operations/workout_template_views.py)

Ownership:

1. management de templates
2. politica de aprovacao do box
3. metadata de template
4. blocos e movimentos persistentes

Abra primeiro aqui quando:

1. a tela de templates quebrar
2. toggle, duplicate, delete ou update de template falhar
3. a politica de aprovacao do box nao persistir

### 3. Corredor do planner

Arquivo:

1. [operations/workout_planner_views.py](../../operations/workout_planner_views.py)

Ownership:

1. tela do planner
2. telemetria do picker
3. apply trusted template pelo cockpit
4. duplicacao do slot anterior

Abra primeiro aqui quando:

1. a rota do planner quebrar
2. picker do planner falhar
3. apply trusted template nao respeitar o fluxo HTTP
4. o cockpit perder comportamento de navegacao ou acao

### 4. Contexto da board de aprovacao

Arquivo:

1. [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py)

Ownership:

1. filtros da board
2. ordenacao dos WODs pendentes
3. checkpoint semanal no contexto da tela
4. assistentes da board
5. montagem do payload da pagina da aprovacao

Abra primeiro aqui quando:

1. a fila pendente vier errada
2. um filtro nao funcionar
3. a tela de aprovacao estiver montando contexto demais ou de menos

### 5. Builders puros da board

Arquivo:

1. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)

Ownership:

1. diff estrutural do WOD
2. preview do aluno
3. leitura assistida de decisao
4. tendencias operacionais
5. maturidade semanal
6. recomendacoes executivas

Abra primeiro aqui quando:

1. o resumo executivo estiver errado
2. o diff do treino estiver estranho
3. o preview do aluno na board divergir
4. a leitura de maturidade ou tendencia estiver incoerente

Regra:

1. este corredor deve permanecer sem `request`, sem redirect e sem messages

### 6. Corredor HTTP da board, history e quick edit

Arquivo:

1. [operations/workout_board_views.py](../../operations/workout_board_views.py)

Ownership:

1. `WorkoutApprovalBoardView`
2. `WorkoutPublicationHistoryView`
3. `OperationsExecutiveSummaryView`
4. `WorkoutStudentRmQuickEditView`

Abra primeiro aqui quando:

1. a rota de board ou history quebrar
2. o resumo executivo falhar na casca HTTP
3. o quick edit de RM falhar no fluxo HTTP

### 7. Historico publicado e pos-publicacao

Arquivo:

1. [operations/workout_published_history.py](../../operations/workout_published_history.py)

Ownership:

1. revisoes publicadas
2. consumo do WOD
3. alertas pos-publicacao
4. follow-up e closure executivo
5. memoria operacional digest
6. assistente executivo do historico publicado

Abra primeiro aqui quando:

1. a parte publicada da board estiver lenta
2. o follow-up nao bater com os dados
3. os alertas pos-publicacao estiverem errados
4. a leitura executiva da historia estiver inconsistente

### 8. Corredor do editor do coach

Arquivo:

1. [operations/workout_editor_views.py](../../operations/workout_editor_views.py)

Ownership:

1. `WorkoutEditorHomeView`
2. `CoachSessionWorkoutEditorView`
3. `WorkoutPrescriptionPreviewView`

Abra primeiro aqui quando:

1. o editor da aula quebrar no fluxo HTTP
2. o redirect do editor-home divergir
3. o preview backend de prescricao falhar

### 9. Mutacoes do WOD

Arquivo:

1. [operations/workout_action_views.py](../../operations/workout_action_views.py)

Ownership:

1. aprovar WOD
2. rejeitar WOD
3. registrar follow-up
4. registrar memoria operacional
5. registrar checkpoint semanal

Abra primeiro aqui quando:

1. uma acao da board nao salva
2. a auditoria de aprovacao falha
3. o redirect ou messages das mutacoes estiverem errados

Regra:

1. action view e mutacao real
2. nao deve virar lugar de leitura pesada

### 10. Suporte compartilhado do WOD

Arquivo:

1. [operations/workout_support.py](../../operations/workout_support.py)

Ownership:

1. serializar snapshot do WOD
2. criar revisao
3. registrar auditoria
4. montar review snapshot
5. montar historico curto do checkpoint
6. helper de semana operacional

Abra primeiro aqui quando:

1. editor, board e action views compartilharem a mesma regra
2. houver duvida sobre revisao e auditoria
3. surgir acoplamento circular entre modulos do WOD

Regra:

1. essa e a caixa de ferramentas compartilhada
2. ela nao deve depender dos corredores HTTP

## Ordem de leitura por tipo de problema

### Problema na tela de aprovacao

Leia:

1. [operations/workout_board_views.py](../../operations/workout_board_views.py)
2. [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py)
3. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)

### Problema em acao de aprovar, rejeitar ou registrar follow-up

Leia:

1. [operations/workout_action_views.py](../../operations/workout_action_views.py)
2. [operations/workout_support.py](../../operations/workout_support.py)
3. [operations/forms.py](../../operations/forms.py)

### Problema no historico publicado e pos-publicacao

Leia:

1. [operations/workout_board_views.py](../../operations/workout_board_views.py)
2. [operations/workout_published_history.py](../../operations/workout_published_history.py)
3. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)
4. [templates/operations/workout_publication_history.html](../../templates/operations/workout_publication_history.html)

### Problema no editor do coach

Leia:

1. [operations/workout_editor_views.py](../../operations/workout_editor_views.py)
2. [operations/workout_editor_context.py](../../operations/workout_editor_context.py)
3. [operations/workout_editor_actions.py](../../operations/workout_editor_actions.py)
4. [operations/workout_support.py](../../operations/workout_support.py)
5. [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html)

### Problema no planner

Leia:

1. [operations/workout_planner_views.py](../../operations/workout_planner_views.py)
2. [operations/workout_planner_context.py](../../operations/workout_planner_context.py)
3. [operations/workout_planner_builders.py](../../operations/workout_planner_builders.py)
4. [templates/operations/workout_planner.html](../../templates/operations/workout_planner.html)

## Ownership atual resumido

1. `workspace_views.py` = workspaces por papel e casca geral
2. `workout_template_views.py` = templates persistentes
3. `workout_planner_views.py` = planner e cockpit
4. `workout_board_views.py` = board, history, summary e RM quick edit
5. `workout_editor_views.py` = editor e preview backend
6. `workout_approval_board_context.py` = montagem do contexto da board
7. `workout_board_builders.py` = inteligencia pura e leitura executiva
8. `workout_published_history.py` = historia publicada e pos-publicacao
9. `workout_action_views.py` = mutacoes reais da board
10. `workout_support.py` = suporte compartilhado do corredor de WOD

## Mapa rapido da suite de testes alvo

Quando a duvida nao for "onde mexer no codigo", mas sim "onde deve morar a cobertura", use como complemento:

1. [../plans/wod-test-ownership-split-corda.md](../plans/wod-test-ownership-split-corda.md)
2. [wod-test-suite-ownership.md](wod-test-suite-ownership.md)

Direcao alvo da suite:

1. `tests/test_coach_wod_editor.py` = editor do coach, inline edit, duplicacao e submit
2. `tests/test_workout_planner_builders.py` = planner, picker e cockpit
3. `tests/test_workout_approval_board.py` = aprovacao, rejeicao, filtros, diff e trilha de decisao
4. `tests/test_workout_post_publication_history.py` = historico publicado, alertas, follow-up e memoria
5. `tests/test_workout_weekly_governance.py` = checkpoint semanal, ritmo, maturidade e governanca

## Antipadroes a evitar

1. voltar a colocar corredores WOD em `workspace_views.py`
2. fazer `workout_action_views.py` depender de corredores HTTP
3. colocar query pesada em builder puro
4. colocar regra de decisao executiva dentro do template
5. duplicar serializacao e auditoria do WOD em varios modulos

## Resumo infantil

Pense no corredor de WOD como uma escola:

1. `workspace_views.py` e a portaria principal do predio
2. `workout_template_views.py` e a biblioteca de moldes
3. `workout_planner_views.py` e a sala do mapa semanal
4. `workout_board_views.py` e a sala de revisao e historico
5. `workout_editor_views.py` e a sala do professor que monta a aula
6. `workout_action_views.py` e o balcao que carimba e registra
7. `workout_support.py` e a caixa de ferramentas da manutencao

Se cada um ficar no seu lugar, a escola funciona.
