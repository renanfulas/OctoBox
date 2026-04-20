<!--
ARQUIVO: inventario vivo da Onda 0 do editor de WOD do coach.

TIPO DE DOCUMENTO:
- inventario tecnico
- baseline de comportamento
- mapa de corte para refatoracao

AUTORIDADE:
- alta para a Onda 0 da frente `coach-session-workout-editor-refactor-corda`

DOCUMENTO PAI:
- [coach-session-workout-editor-refactor-corda.md](coach-session-workout-editor-refactor-corda.md)

QUANDO USAR:
- quando a duvida for o que exatamente o editor do coach faz hoje
- quando precisarmos separar leitura, mutacao e apresentacao sem quebrar o fluxo
- quando quisermos validar o baseline antes de mover codigo

POR QUE ELE EXISTE:
- evita refatorar no escuro
- registra os pontos de ownership real do editor
- congela o contrato minimo antes das ondas estruturais
-->

# Onda 0 - Inventario do editor de WOD do coach

## Escopo mapeado

Alvo atual:

1. [operations/workspace_views.py](../../operations/workspace_views.py) na classe `CoachSessionWorkoutEditorView`

Superficie visual principal:

1. [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html)

Cobertura principal atual:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

Formularios usados:

1. [operations/forms.py](../../operations/forms.py)

## Mapa de responsabilidades atuais

Hoje a classe mistura cinco grupos de responsabilidade.

### 1. Entrada HTTP e carregamento base

Responsabilidades:

1. carregar `ClassSession` em `dispatch`
2. acoplar `self.session` para o resto da view
3. expor `get()` e `post()`

Ponto de codigo:

1. `dispatch`
2. `get`
3. `post`

### 2. Leitura e bootstrap de dominio

Responsabilidades:

1. descobrir workout existente
2. criar workout lazily quando necessario

Ponto de codigo:

1. `_get_workout`
2. `_get_or_create_workout`

Observacao:

1. esse trecho pertence mais a `action/workflow` do que a view HTTP

### 3. Apresentacao e payload de UI

Responsabilidades:

1. montar `operation_page`
2. definir hero e assets da tela

Ponto de codigo:

1. `_build_page_payload`

Observacao:

1. esse trecho pertence mais a `presenter`

### 4. Leitura pesada do editor

Responsabilidades:

1. construir preview de RM
2. montar forms iniciais
3. buscar sessoes elegiveis para duplicacao
4. montar contexto completo do template

Ponto de codigo:

1. `_build_rm_preview`
2. `_build_context`

Observacao:

1. esse trecho pertence mais a `query + presenter`

### 5. Mutacao real por intent

Responsabilidades:

1. salvar workout
2. adicionar, atualizar e remover block
3. adicionar, atualizar e remover movement
4. enviar para aprovacao
5. duplicar workout
6. registrar auditoria
7. atualizar `status`, `version` e revisoes

Ponto de codigo:

1. `post`

Observacao:

1. esse trecho pertence mais a `dispatcher + actions`

## Mapa de intents atuais do POST

O `post()` atual opera com nove intents explicitos:

1. `save_workout`
2. `add_block`
3. `delete_block`
4. `update_block`
5. `add_movement`
6. `delete_movement`
7. `update_movement`
8. `submit_for_approval`
9. `duplicate_workout`

Fallback atual:

1. `messages.error('Acao de WOD nao reconhecida neste fluxo.')`
2. redirect para o proprio editor

## Contrato de mutacao observado

### Regras repetidas no fluxo atual

As mutacoes repetem uma familia de regras importantes:

1. edicao em WOD `published` volta para `draft`
2. edicao em WOD `rejected` volta para `draft`
3. em alguns casos, edicao em `pending_approval` tambem volta para `draft`
4. limpeza de `approved_by` e `approved_at` acontece em varios ramos
5. `version` sobe em varios ramos
6. auditoria e revisao sao registradas por intent

### Ponto de atencao estrutural

Esse conjunto hoje esta duplicado dentro do `post()`.

Traducao tecnica:

1. existe regra compartilhada suficiente para justificar extração para actions

## Contrato minimo de leitura do template

O template atual depende diretamente destes blocos de contexto:

1. `operation_page`
2. `session`
3. `workout`
4. `workout_form`
5. `block_form`
6. `movement_form`
7. `session_rm_preview`
8. `duplicate_sessions`
9. `duplicate_form`

### Estrutura visual relevante do template

O template possui quatro areas principais:

1. cabecalho do WOD com status, versao, submit e duplicacao
2. estrutura de blocos com edicao inline
3. formulario de adicionar movement
4. preview de RM da turma

### Dependencias visuais importantes

O template hoje usa:

1. `workout.status` para pills de status
2. `workout.version` para pill de versao
3. `workout.rejection_reason` para feedback de rejeicao
4. `session_rm_preview.cards`
5. `session_rm_preview.reserved_students_count`
6. `duplicate_sessions`

## Contrato atual do preview de RM

### Entrada funcional observada

O preview depende de:

1. `attendances` da sessao com status em:
   - `BOOKED`
   - `CHECKED_IN`
   - `CHECKED_OUT`
2. movements com `load_type == PERCENTAGE_OF_RM`
3. `StudentExerciseMax` por `student_id + exercise_slug`

### Saida observada

O preview retorna dicionario com:

1. `reserved_students_count`
2. `cards`
3. `empty_copy`

Cada card carrega:

1. `block_title`
2. `movement_label`
3. `prescription_label`
4. `load_context_label`
5. `coverage_label`
6. `range_label`
7. `tracked_students`
8. `missing_students`
9. `missing_students_label`
10. `missing_students_remaining`

### Leitura de performance

Pontos de custo relevantes:

1. loop por attendance para montar alunos
2. loop por block e movement para achar `%RM`
3. uma query unica de `StudentExerciseMax`, o que e bom
4. loop final por movement e por student, o que merece medicao mas ainda esta coerente

Leitura profissional:

1. o preview ainda nao esta "ruim por definicao"
2. mas ele ja e denso o bastante para merecer ownership proprio em `query + presenter`

## Cobertura de testes atual

Arquivo principal:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

Fluxos cobertos:

1. exibir CTA de criar WOD no workspace do coach
2. criar workout, block e movement
3. enviar para aprovacao
4. atualizar block e movement inline
5. duplicar workout para outra sessao como `draft`
6. exibir preview de RM com alunos booked/check-in
7. explicar estado vazio quando nao existe `%RM`

### Lacunas percebidas na Onda 0

Ainda valeria cobertura extra para:

1. `delete_block`
2. `delete_movement`
3. fallback de intent desconhecida
4. reset de `published -> draft`
5. reset de `pending_approval -> draft` nas edicoes
6. erro de duplicacao para aula que ja possui WOD

## Melhor corte por capacidade

Com base no estado atual, o proximo corte mais seguro fica assim:

### Dispatcher

Sair primeiro de `post()`:

1. mapa `intent -> handler`

### Actions

Agrupamento natural:

1. workout:
   - `save_workout`
   - `submit_for_approval`
   - `duplicate_workout`
2. block:
   - `add_block`
   - `update_block`
   - `delete_block`
3. movement:
   - `add_movement`
   - `update_movement`
   - `delete_movement`

### Queries

Agrupamento natural:

1. carregar sessao + workout
2. duplicate sessions snapshot
3. rm preview snapshot

### Presenter

Agrupamento natural:

1. `operation_page`
2. labels e cards do preview de RM
3. contexto final consumido pelo template

## Risco principal da frente

O maior risco nao e mover codigo.

O maior risco e:

1. quebrar o contrato visual e comportamental do editor enquanto tentamos melhorar a estrutura

Em linguagem simples:

1. nao adianta organizar a oficina se o carro nao liga na hora da aula

## Check de pronto da Onda 0

Esta onda pode ser considerada fechada porque:

1. os intents estao mapeados
2. os grupos de responsabilidade estao separados
3. o contrato minimo de contexto foi registrado
4. a cobertura existente do editor foi localizada
5. as lacunas mais relevantes ficaram explicitas
