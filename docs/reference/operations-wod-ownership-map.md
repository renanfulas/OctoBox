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

1. leitura de workspace
2. montagem da board
3. historico publicado
4. mutacoes reais
5. suporte compartilhado

Em linguagem simples:

1. a cozinha, o caixa e a recepcao nao dividem mais o mesmo balcao

## Mapa rapido

### 1. Casca HTTP de workspace

Arquivo:

1. [operations/workspace_views.py](../../operations/workspace_views.py)

Ownership:

1. telas operacionais por papel
2. editor do WOD do coach
3. casca fina da `WorkoutApprovalBoardView`

Abra primeiro aqui quando:

1. a rota da tela quebrou
2. o contexto base do workspace sumiu
3. o editor do coach falhou no fluxo HTTP

Nao deveria concentrar:

1. historico publicado
2. action views da board
3. heuristica compartilhada do WOD

### 2. Contexto da board de aprovacao

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

### 3. Builders puros da board

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

### 4. Historico publicado e pos-publicacao

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

### 5. Mutacoes do WOD

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

### 6. Suporte compartilhado do WOD

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
2. ela nao deve depender de `workspace_views.py`

## Ordem de leitura por tipo de problema

### Problema na tela de aprovacao

Leia:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py)
3. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)

### Problema em acao de aprovar, rejeitar ou registrar follow-up

Leia:

1. [operations/workout_action_views.py](../../operations/workout_action_views.py)
2. [operations/workout_support.py](../../operations/workout_support.py)
3. [operations/forms.py](../../operations/forms.py)

### Problema no historico publicado e pos-publicacao

Leia:

1. [operations/workout_published_history.py](../../operations/workout_published_history.py)
2. [operations/workout_board_builders.py](../../operations/workout_board_builders.py)
3. [templates/operations/workout_approval_board.html](../../templates/operations/workout_approval_board.html)

### Problema no editor do coach

Leia:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/workout_support.py](../../operations/workout_support.py)
3. [operations/forms.py](../../operations/forms.py)
4. [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html)

## Ownership atual resumido

1. `workspace_views.py` = entrada e casca HTTP
2. `workout_approval_board_context.py` = montagem do contexto da board
3. `workout_board_builders.py` = inteligencia pura e leitura executiva
4. `workout_published_history.py` = historia publicada e pos-publicacao
5. `workout_action_views.py` = mutacoes reais da board
6. `workout_support.py` = suporte compartilhado do corredor de WOD

## Mapa rapido da suite de testes alvo

Quando a duvida nao for "onde mexer no codigo", mas sim "onde deve morar a cobertura", use como complemento:

1. [../plans/wod-test-ownership-split-corda.md](../plans/wod-test-ownership-split-corda.md)
2. [wod-test-suite-ownership.md](wod-test-suite-ownership.md)

Direcao alvo da suite:

1. `tests/test_coach_wod_editor.py` = editor do coach, inline edit, duplicacao e submit
2. `tests/test_workout_approval_board.py` = aprovacao, rejeicao, filtros, diff e trilha de decisao
3. `tests/test_workout_post_publication_history.py` = historico publicado, alertas, follow-up e memoria
4. `tests/test_workout_weekly_governance.py` = checkpoint semanal, ritmo, maturidade e governanca

## Antipadroes a evitar

1. voltar a colocar action views em `workspace_views.py`
2. fazer `workout_action_views.py` depender de `workspace_views.py`
3. colocar query pesada em builder puro
4. colocar regra de decisao executiva dentro do template
5. duplicar serializacao e auditoria do WOD em varios modulos

## Resumo infantil

Pense no corredor de WOD como uma escola:

1. `workspace_views.py` e a porta da escola
2. `workout_approval_board_context.py` e a secretaria que organiza a sala
3. `workout_board_builders.py` e o professor que pensa
4. `workout_published_history.py` e o caderno de ocorrencias
5. `workout_action_views.py` e o balcão que carimba e registra
6. `workout_support.py` e a caixa de ferramentas da manutencao

Se cada um ficar no seu lugar, a escola funciona.
