<!--
ARQUIVO: inventario vivo da Onda 0 para o split da suite de WOD.

TIPO DE DOCUMENTO:
- inventario tecnico
- baseline de refatoracao

AUTORIDADE:
- alta para orientar a primeira quebra segura da suite

DOCUMENTOS PAIS:
- [wod-test-ownership-split-corda.md](wod-test-ownership-split-corda.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)

QUANDO USAR:
- antes de mover testes de `tests/test_coach_wod_editor.py`
- quando a duvida for qual teste vai para qual arquivo
- quando precisarmos validar se a suite continua cobrindo os corredores certos

POR QUE ELE EXISTE:
- evita split por intuicao
- congela o mapa atual da suite antes das extracoes
- reduz risco de perder cobertura de transicao
-->

# Onda 0 - Inventario da suite de WOD

## Estado observado

Arquivo atual:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)
2. [tests/test_workout_approval_board.py](../../tests/test_workout_approval_board.py)
3. [tests/test_workout_post_publication_history.py](../../tests/test_workout_post_publication_history.py)
4. [tests/test_workout_weekly_governance.py](../../tests/test_workout_weekly_governance.py)

Medidas atuais:

1. `tests/test_coach_wod_editor.py` agora ficou focado no editor do coach
2. `tests/test_workout_approval_board.py` agora protege o corredor dedicado da aprovacao
3. `tests/test_workout_post_publication_history.py` agora protege historico publicado, alertas e follow-up
4. `tests/test_workout_weekly_governance.py` agora protege governanca semanal e leitura executiva curta
5. a distribuicao atual continua cobrindo 19 testes ao todo

## Corredores identificados

### 1. Editor do coach

Responsabilidade:

1. criar WOD
2. editar bloco e movimento inline
3. duplicar treino
4. submeter para aprovacao

Testes atuais:

1. `test_coach_workspace_shows_wod_action_for_session`
2. `test_coach_can_create_submit_block_and_movement`
3. `test_coach_can_update_block_and_movement_inline`
4. `test_coach_can_duplicate_workout_to_another_session_as_draft`

Arquivo alvo:

1. [tests/test_coach_wod_editor.py](../../tests/test_coach_wod_editor.py)

### 2. Board de aprovacao

Responsabilidade:

1. aprovar
2. rejeitar
3. exigir confirmacao de mudanca sensivel
4. filtrar fila
5. renderizar resumo, diff e trilha de decisao

Testes atuais:

1. `test_manager_can_approve_pending_workout`
2. `test_manager_can_approve_with_optional_decision_reason`
3. `test_manager_must_confirm_sensitive_changes_before_approving`
4. `test_owner_can_reject_pending_workout_with_reason`
5. `test_approval_board_renders_richer_review_summary`
6. `test_approval_board_renders_diff_against_last_published_revision`
7. `test_approval_board_renders_decision_trail_in_timeline`
8. `test_approval_board_filters_sensitive_today_and_coach`

Arquivo alvo:

1. [tests/test_workout_approval_board.py](../../tests/test_workout_approval_board.py)

### 3. Historico publicado e pos-publicacao

Responsabilidade:

1. renderizar historico executivo
2. filtrar historico por motivo
3. alertas pos-publicacao
4. follow-up de acao sugerida
5. memoria operacional curta

Testes atuais:

1. `test_approval_board_renders_post_publication_executive_history`
2. `test_approval_board_filters_post_publication_history_by_reason`
3. `test_approval_board_surfaces_post_publication_operational_alerts`
4. `test_manager_can_register_follow_up_result_for_suggested_action`

Arquivo alvo:

1. [tests/test_workout_post_publication_history.py](../../tests/test_workout_post_publication_history.py)

### 4. Governanca semanal e leitura executiva

Responsabilidade:

1. checkpoint semanal
2. ritmo do ritual
3. maturidade operacional
4. alerta gerencial leve

Testes atuais:

1. `test_approval_board_surfaces_light_management_alert_for_consistent_improvement`
2. `test_manager_can_register_weekly_management_checkpoint`
3. `test_weekly_checkpoint_history_surfaces_rhythm_changes`

Arquivo alvo:

1. [tests/test_workout_weekly_governance.py](../../tests/test_workout_weekly_governance.py)

## Baseline de comandos

Comandos minimos para validar a trilha:

1. `python manage.py test tests.test_coach_wod_editor`
2. `python manage.py check`

Comandos esperados apos o split:

1. `python manage.py test tests.test_coach_wod_editor`
2. `python manage.py test tests.test_workout_approval_board`
3. `python manage.py test tests.test_workout_post_publication_history`
4. `python manage.py test tests.test_workout_weekly_governance`
5. `python manage.py check`

## Setup compartilhado observado

Hoje existe repeticao forte de setup em torno de:

1. `bootstrap_roles`
2. criacao de `coach`, `manager` e `owner`
3. criacao da sessao base
4. criacao de `student_alpha` e `student_beta`
5. login inicial no coach

### Regra de extracao

Vale extrair somente:

1. o setup comum de papeis e sessao
2. helpers pequenos para login por papel
3. helpers pequenos para criar workout publicado ou pendente quando reduzir ruido
4. suporte compartilhado curto em [tests/workout_test_support.py](../../tests/workout_test_support.py)

Nao vale extrair agora:

1. mini framework generico de factories
2. helper que esconda toda a leitura do teste
3. classe base que faca mais de uma tela por vez

## Riscos congelados da Onda 0

1. misturar testes de board e historico no mesmo arquivo novo por comodidade
2. extrair helpers demais e matar a legibilidade
3. perder smoke de transicao coach -> aprovacao -> publicado
4. criar dependencia acidental de ordem entre arquivos

## Resultado esperado desta onda

Ao final da Onda 0:

1. sabemos para onde cada teste vai
2. sabemos qual setup minimo vale reaproveitar
3. temos baseline para validar a quebra
4. a primeira extracao real pode comecar sem chute

## Estado apos a Onda 2

Esta primeira extracao real ja foi executada:

1. o corredor de aprovacao saiu de `tests/test_coach_wod_editor.py`
2. nasceu [tests/test_workout_approval_board.py](../../tests/test_workout_approval_board.py)
3. a suite continua verde no split isolado e no baseline conjunto

## Estado apos a Onda 3

Esta segunda extracao real ja foi executada:

1. o historico publicado e o pos-publicacao sairam de `tests/test_coach_wod_editor.py`
2. nasceu [tests/test_workout_post_publication_history.py](../../tests/test_workout_post_publication_history.py)
3. `tests/test_coach_wod_editor.py` ficou mais fiel ao seu ownership real
4. a suite continua verde no split isolado e no baseline conjunto

## Estado apos a Onda 4

Esta terceira extracao real ja foi executada:

1. a governanca semanal saiu de `tests/test_coach_wod_editor.py`
2. nasceu [tests/test_workout_weekly_governance.py](../../tests/test_workout_weekly_governance.py)
3. `tests/test_coach_wod_editor.py` ficou praticamente restrito ao corredor do coach
4. os quatro corredores agora possuem arquivo proprio
5. a suite continua verde no split isolado e no baseline conjunto
