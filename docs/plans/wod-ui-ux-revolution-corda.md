<!--
ARQUIVO: C.O.R.D.A. da revolucao UI/UX do corredor de WOD (OWNER/MANAGER/COACH).

TIPO DE DOCUMENTO:
- plano arquitetural, operacional e de front-end
- trilho de execucao por ondas pequenas e testaveis

AUTORIDADE:
- alta para a evolucao do fluxo operacional de WOD nas telas /operacao/wod/*
- alta para a hierarquia de papeis OWNER/MANAGER/COACH dentro do corredor
- subordinada a octobox-architecture-model.md e documentation-authority-map.md

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)
- [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)
- [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md)

DOCUMENTOS IRMAOS:
- [coach-session-workout-editor-refactor-corda.md](coach-session-workout-editor-refactor-corda.md)
- [operations-queries-and-published-history-corda.md](operations-queries-and-published-history-corda.md)
- [wod-test-ownership-split-corda.md](wod-test-ownership-split-corda.md)

QUANDO USAR:
- quando a duvida for como evoluir a UI/UX do corredor WOD sem quebrar o contrato do aluno
- quando precisarmos amarrar hierarquia de papeis na mesma superficie
- quando quisermos planejar semana/mes em minutos e nao em horas
- quando a fila de aprovacao estiver custando atencao demais
- quando a integracao WOD <-> RM do aluno estiver escondida atras de cliques

POR QUE ELE EXISTE:
- hoje o corredor WOD tem 4 superficies irmas sem narrativa unica
- copy explicativa permanente ocupa area de decisao
- OWNER nao consegue planejar a semana sem depender do coach
- a ponte WOD <-> RM existe no dado mas nao existe na escrita
- cada onda precisa ser pequena, testavel e reversivel

O QUE ESTE ARQUIVO FAZ:
1. formaliza o estado atual observado e o atrito diagnosticado
2. define a hierarquia OWNER/MANAGER/COACH como lentes da mesma tela
3. define o alvo arquitetural e de front-end (tokens, naming, camadas)
4. organiza a execucao em 7 ondas com contrato, failure modes e rollback
5. lista arquivos a criar, alterar e remover com evidencia
6. registra o que nao fazer agora para evitar overengineering

PONTOS CRITICOS:
- o corredor /aluno/ e inviolavel; a ponte e feita via movement_slug
- o arquivo workspace_views.py nao pode reabsorver responsabilidade
- builders puros nao podem depender de request
- feature flag por box e obrigatorio nas ondas 3 e 4
- todo avanco de onda exige baseline do `scripts/frontend_forensics.py`
-->

# C.O.R.D.A. - Revolucao UI/UX do corredor de WOD (OWNER/MANAGER/COACH)

## C - Contexto

### Estado observado

1. Quatro superficies irmas sem narrativa unica:
   - [operations/workspace_views.py](../../operations/workspace_views.py) publica `WorkoutEditorHomeView`, `WorkoutApprovalBoardView`, `WorkoutPublicationHistoryView`, `CoachSessionWorkoutEditorView`
   - Templates correspondentes em [templates/operations/](../../templates/operations/) e includes em [templates/operations/includes/](../../templates/operations/includes/)
2. O template da board ([templates/operations/workout_approval_board.html](../../templates/operations/workout_approval_board.html)) carrega 3 blocos descritivos permanentes (`Radar da fila`, `Leitura rapida da revisao`, `Decisao curta para publicar sem ruido`) que ocupam area de decisao.
3. Acoes operacionais vivem em endpoints separados sem agrupamento visual:
   - `WorkoutApprovalActionView` (`approve`, `reject`)
   - `WorkoutFollowUpActionView`
   - `WorkoutRmGapActionView`
   - `WorkoutOperationalMemoryCreateView`
   - `WorkoutWeeklyCheckpointUpdateView`
4. Nao existe uma superficie de planejamento semanal/mensal: o OWNER so ve WOD depois do coach submeter.
5. CSS dedicado concentrado em [static/css/design-system/operations/dev-coach/coach.css](../../static/css/design-system/operations/dev-coach/coach.css) com classes `coach-wod-*` duplicando responsabilidades de `table-card`, `pill` e `eyebrow` que ja existem no design system.
6. A ponte WOD <-> RM existe no dado: `SessionWorkoutMovement.movement_slug` e `StudentExerciseMax.exercise_slug` compartilham o mesmo espaco de nomes. Mas a UI do coach nao aproveita: o coach digita slug a mao e a prescricao em percentual nao tem preview de carga recomendada.

### Atrito diagnosticado

1. **Decisao distribuida**: aprovar um WOD exige ler ~4 blocos de copy e ~6 pills.
2. **Zero CTA dominante**: cada card tem 3-5 botoes de mesmo peso.
3. **OWNER sem autonomia**: depende do coach para existir um WOD.
4. **Sem narrativa temporal**: fila linear no lugar de grade semanal.
5. **Calculadora mental oculta**: coach prescreve percentual sem ver a traducao para carga.
6. **CSS sobrecarregado**: `coach-wod-*` cresce em vez de reaproveitar primitivos.

### Leitura arquitetural

Pelo modelo oficial ([octobox-architecture-model.md](../architecture/octobox-architecture-model.md)):

1. view HTTP pertence ao Nivel 1 e deve ser casca fina.
2. payload e leitura organizada devem morar em context + builders puros.
3. mutacao deve morar em action views dedicadas.
4. estilos devem usar tokens canonicos em [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css).

### Tese do problema

A UI do WOD hoje resolve autoria e aprovacao em paginas separadas, mas nao resolve **planejamento** nem **leitura rapida de decisao**. Resultado: o OWNER gasta tempo onde nao deveria e o COACH perde a chance de prescrever com consciencia da carga do aluno.

---

## O - Objetivo

### Outcome de produto

1. OWNER planeja a semana inteira em <= 3 min.
2. OWNER planeja o mes em <= 5 min.
3. MANAGER aprova fila do dia (sem sensivel) em <= 60 s.
4. COACH publica WOD em <= 3 cliques a partir do login.
5. Zero superficie com mais de 1 CTA primario acima da dobra.
6. Zero copy explicativa permanente em card.

### Outcome tecnico

1. Uma unica tela-mae `/operacao/wod/` com tres zooms (mes/semana/aula).
2. `WorkoutPlannerContext` + `WorkoutPlannerBuilders` puros e testaveis.
3. `WorkoutTemplate` como entidade reutilizavel por box.
4. `Box.wod_approval_policy` como politica explicita.
5. CSS do corredor WOD reduzido >= 30% e usando tokens canonicos.
6. Linhas de template do corredor WOD reduzidas >= 35%.

### Sinais mensuraveis

| Metrica | Como medir | Alvo |
|---|---|---|
| Tempo medio `approve` por WOD | structlog em `WorkoutApprovalActionView` | <= 8 s |
| Cliques OWNER login -> semana pronta | log de navegacao estruturado | <= 6 |
| WODs publicados sem rejeicao | razao sobre 30 dias | >= 85% |
| Linhas de template corredor WOD | `wc -l` pre/pos | <= 65% da baseline |
| Regras CSS `coach-wod-*` | diff de [coach.css](../../static/css/design-system/operations/dev-coach/coach.css) | <= 70% da baseline |
| Superficies HTTP do corredor WOD | contagem de rotas | 3 |
| Tempo de render do Planner (p95) | telemetria Django | <= 400 ms |

### Nao-objetivo

1. Reescrever `SessionWorkout`/`SessionWorkoutBlock`/`SessionWorkoutMovement`.
2. Mudar contrato de leitura do [student_app/views/wod_context.py](../../student_app/views/wod_context.py).
3. Mover regra de heuristica para template.
4. Substituir o design-system existente.
5. Introduzir framework JS novo.

---

## R - Restricoes

### Restricoes de produto

1. O corredor `/aluno/` e inviolavel (ver [../reference/student_app_map](../../student_app/)).
2. Permissoes OWNER/MANAGER/COACH mantem o contrato atual de ACL.
3. Mobile-first obrigatorio; breakpoints canonicos da casa.
4. Contraste AA minimo; ARIA em grade e drawer.
5. Feature-flag por box obrigatoria nas ondas 3 e 4.

### Restricoes arquiteturais

1. Sem rewrite: `operations/workout_approval_board_context.py`, `operations/workout_board_builders.py`, `operations/workout_support.py`, `operations/workout_action_views.py` mantem contratos estaveis.
2. Builder puro **nao pode** depender de `request`, redirect ou messages.
3. Action view **nao pode** virar lugar de leitura pesada.
4. `workspace_views.py` so recebe cascas finas; qualquer logica nova vai para modulo dedicado.
5. Migracoes com backfill zero-downtime; campo novo sempre `null=True` ou default estavel.

### Restricoes de front-end

1. Toda nova regra CSS precisa usar tokens de [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css).
2. Naming BEM: `.wod-planner`, `.wod-planner__cell`, `.wod-planner__cell--published`.
3. CSS novo mora em [static/css/design-system/operations/workspace/](../../static/css/design-system/operations/workspace/) com arquivos dedicados: `wod-planner.css`, `wod-inbox.css`, `wod-drawer.css`, `wod-editor.css`.
4. Registro de assets via `build_catalog_assets` (padrao [catalog/presentation/shared.py](../../catalog/presentation/shared.py)).
5. Zero `style=""` inline, zero `<style>` em template, zero `!important` novo.
6. JS em arquivos dedicados em [static/js/operations/](../../static/js/operations/), comunicacao via `data-*`.

### Restricoes de processo

1. Cada onda = 1 PR, 1 objetivo primario, DoD mensuravel.
2. Onda 0 obrigatoria antes de qualquer mutacao visual.
3. Rollback trivial: toggle de flag ou revert do PR.
4. Testes existentes nao podem regredir; testes novos por onda.

---

## D - Decisoes

### D1 - Tres superficies, nao quatro

| Superficie | Rota canonica | Papel primario | Substitui |
|---|---|---|---|
| Planner | `/operacao/wod/planner/` | OWNER/MANAGER | `workout-editor-home` |
| Inbox | `/operacao/wod/aprovacoes/` | MANAGER/OWNER | mantida, refundida |
| Editor | `/operacao/coach/aula/<id>/wod/` | COACH | mantida, enxuta |

Historico publicado vira **drawer lateral** dentro do Planner. Rota `/operacao/wod/historico/` mantida como redirect 302 para `planner/?drawer=history` (estrangulador).

### D2 - Uma tela, tres lentes (zoom)

```
MES    (OWNER default)          -> grade 4-5 semanas x 7 dias
 SEMANA (MANAGER default)        -> grade 7 dias x N slots
  AULA  (COACH default)          -> WOD vertical + painel RM ao lado
```

Navegacao: clicar celula faz zoom-in; `Esc` volta. Papel define ponto de pouso no login, **nao** define o que pode ser visto.

### D3 - Hierarquia de acoes por papel

**OWNER (estrategico):**
```
[ Publicar semana ]           <- CTA primario
  Duplicar semana anterior
  Aplicar template do box
  Atribuir coach
  Aprovar em lote (auditado)
  -----
  Metricas | RM gaps | Governanca   (drawer)
```

**MANAGER (tatico):**
```
[ Aprovar ]                   <- CTA primario, atalho ENTER
  Rejeitar com motivo
  Pedir ajuste ao coach
  Reatribuir aula
  -----
  Fila sensivel | Follow-up         (drawer)
```

**COACH (operacional):**
```
[ Publicar ] OU [ Enviar p/ aprovacao ]   <- um dos dois, pela politica
  Duplicar WOD do mesmo slot semana passada
  Aplicar template
  -----
  RM dos alunos desta aula                 (painel lateral sempre visivel)
```

### D4 - Inbox padrao "Stripe Inbox"

1. Lista densa a esquerda (title + 1 pill critica).
2. Preview rico a direita.
3. CTA unico: **Aprovar**; atalhos `j/k/ENTER`.
4. Itens com `diff_snapshot.is_sensitive=True` ficam fora do batch por design.
5. Command palette `Ctrl+K` para todas as acoes secundarias.

### D5 - Planner padrao "Netflix grid temporal"

1. Grade 7xN, celula = `ClassSession` + estado do `SessionWorkout`.
2. Estados visuais: `vazio`, `rascunho`, `pendente`, `publicado`, `sensivel`.
3. Menu contextual de 1 clique por celula.
4. Selecao multipla via `Shift+clique` para batch.
5. Keyboard: setas navegam, `ENTER` abre editor, `Ctrl+D` duplica.

### D6 - Editor COACH enxuto

1. Abre no estado "ontem+1": pre-popula com ultimo WOD do mesmo slot.
2. Autocomplete de movimento que resolve `movement_slug` sem digitacao.
3. Ao escolher movimento com RM cadastrado no box, `load_type` default vira `PERCENTAGE`.
4. Preview de prescricao em tempo real via [student_app/domain/workout_prescription.py](../../student_app/domain/workout_prescription.py).
5. CTA unico definido pela politica do box; nunca os dois ao mesmo tempo.

### D7 - WorkoutTemplate como entidade leve

```
WorkoutTemplate
  box (FK)
  name
  default_block_kinds
  is_trusted (bool)
  -> WorkoutTemplateBlock
       -> WorkoutTemplateMovement (movement_slug, sets, reps, default_load_type, default_percentage)
```

Aplicar template = `INSERT` em `SessionWorkoutBlock` + `SessionWorkoutMovement`. Zero campo novo no schema de sessao/workout/block/movement.

### D8 - Politica de aprovacao por box

Campo unico `Box.wod_approval_policy`:
- `strict` -> todo WOD passa por aprovacao (default)
- `trusted_template` -> WOD aplicado de template `is_trusted=True` publica direto
- `coach_autonomy` -> coach com flag `is_trusted_author` publica direto

Metodo `SessionWorkout.should_require_approval(coach, source)` centraliza a decisao.

### D9 - Silencio visual e copy on-demand

1. Remover copy descritiva permanente de todos os heads do corredor.
2. Copy migra para tooltip (`aria-describedby`) via icone `?` no eyebrow.
3. Eyebrows genericos saem; rotulos viram contagens ("7 pendentes - 2 sensiveis").

### D10 - Token-first para cores de estado

Novos tokens em [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css):

```
--wod-state-empty
--wod-state-draft
--wod-state-pending
--wod-state-published
--wod-state-sensitive
--wod-cell-min-size: 72px
--wod-planner-gap: var(--space-1)
```

Componentes consomem tokens; nenhuma cor hardcoded em componente.

---

## A - Acoes (execucao por ondas)

Cada onda segue o contrato:

```
OBJETIVO PRIMARIO  - uma frase, um resultado
CONTRATO DE ENTRADA - o que a onda assume pronto
CONTRATO DE SAIDA   - o que entrega para a proxima
DoD                 - criterios objetivos de pronto
FAILURE MODES       - o que pode dar errado e como detectar
ROLLBACK            - como desfazer em 1 passo
```

### Onda 0 - Baseline, telemetria e forensics

**OBJETIVO:** estabelecer linha de comparacao antes de qualquer mudanca visual.

**CONTRATO DE ENTRADA:** corredor WOD atual em producao.

**CONTRATO DE SAIDA:**
1. Doc `docs/plans/wod-ui-ux-revolution-wave0-inventory.md` com metricas de baseline:
   - linhas por template (`wc -l`) do corredor WOD
   - regras CSS `coach-wod-*` (contagem)
   - rotas do corredor WOD (contagem)
   - tempo medio atual de `approve` por WOD (amostragem de 100 eventos)
2. Saida de `py .agents/skills/octobox-ui-cleanup-auditor/scripts/frontend_forensics.py` com foco em `coach-wod-*`.
3. Instrumentacao structlog em [operations/workout_action_views.py](../../operations/workout_action_views.py) emitindo `wod_action_duration_ms`.

**DoD:**
- inventario publicado
- telemetria emitindo em staging
- zero alteracao de UI

**FAILURE MODES:** telemetria acidental em producao sem amostragem -> DoD exige toggle via settings.

**ROLLBACK:** revert do PR; nenhum impacto visual para desfazer.

---

### Onda 1 - Silencio visual (baixo risco)

**OBJETIVO:** remover copy descritiva permanente sem tocar em logica.

**CONTRATO DE ENTRADA:** baseline da Onda 0 congelado.

**CONTRATO DE SAIDA:** templates do corredor WOD com -35% linhas e zero `<p>` explicativo permanente em heads.

**ARQUIVOS ALTERADOS:**
- [templates/operations/workout_approval_board.html](../../templates/operations/workout_approval_board.html)
- [templates/operations/workout_editor_home.html](../../templates/operations/workout_editor_home.html)
- [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html)
- [templates/operations/workout_publication_history.html](../../templates/operations/workout_publication_history.html)
- [templates/operations/includes/wod_corridor_tabs.html](../../templates/operations/includes/wod_corridor_tabs.html)

**CRIADOS:**
- [templates/operations/includes/wod_tooltip.html](../../templates/operations/includes/wod_tooltip.html) - componente `?` com `aria-describedby` e conteudo via `{% block %}`.

**DoD:**
- `wc -l` do corredor WOD cai >= 20%
- `grep -r "student-copy\|operation-copy"` no corredor = 0 em heads
- lighthouse A11y >= 95 nas tres telas
- testes existentes passando

**FAILURE MODES:** remover copy que na verdade era contrato de produto -> revisar com product owner antes do merge.

**ROLLBACK:** revert do PR; sem migracao envolvida.

---

### Onda 2 - Inbox lista+preview e command palette

**OBJETIVO:** transformar a board de aprovacao em inbox densa com 1 CTA primario.

**CONTRATO DE ENTRADA:** Onda 1 merged.

**CONTRATO DE SAIDA:**
1. Board com layout split pane.
2. Atalhos `j/k/ENTER` funcionais.
3. Batch approve disponivel para itens nao-sensiveis.
4. Command palette `Ctrl+K` com todas as acoes secundarias.

**PRS:**

**PR 2.1 - Layout e atalhos**
- ALTERADO: [templates/operations/workout_approval_board.html](../../templates/operations/workout_approval_board.html)
- ALTERADO: [static/css/design-system/operations/dev-coach/coach.css](../../static/css/design-system/operations/dev-coach/coach.css) (remove classes `coach-wod-summary-*`, `coach-wod-review-digest`, `coach-wod-review-signal-grid`)
- CRIADO: [static/css/design-system/operations/workspace/wod-inbox.css](../../static/css/design-system/operations/workspace/wod-inbox.css) com classes BEM `.wod-inbox`, `.wod-inbox__list`, `.wod-inbox__item`, `.wod-inbox__preview`, modifiers `--focused`, `--sensitive`
- CRIADO: [static/js/operations/wod_inbox.js](../../static/js/operations/wod_inbox.js) com `data-wod-inbox-key` e atalhos
- ALTERADO: [operations/workout_approval_board_context.py](../../operations/workout_approval_board_context.py) expondo `approval_inbox_items` (dataclass dedicada)

**PR 2.2 - Batch approve**
- CRIADO: `WorkoutApprovalBatchActionView` em [operations/workout_action_views.py](../../operations/workout_action_views.py)
- ALTERADO: [operations/urls.py](../../operations/urls.py) adicionando `operacao/wod/aprovacoes/lote/`
- CRIADO: `operations/actions/workout_batch_approval.py` com validacao `diff_snapshot.is_sensitive=False` obrigatoria
- TESTE: `tests/test_workout_approval_board.py` com caso "batch aprova nao-sensiveis e deixa sensiveis intactos"

**PR 2.3 - Command palette**
- CRIADO: [templates/operations/includes/wod_command_palette.html](../../templates/operations/includes/wod_command_palette.html)
- CRIADO: [static/js/operations/wod_command_palette.js](../../static/js/operations/wod_command_palette.js)
- CRIADO: [static/css/design-system/operations/workspace/wod-command-palette.css](../../static/css/design-system/operations/workspace/wod-command-palette.css)
- Comandos disponiveis via `data-wod-command`: `approve`, `reject`, `follow-up`, `rm-gap`, `memory`, `weekly-checkpoint`

**DoD:**
- tempo medio `approve` em staging (p50) cai >= 40% vs baseline
- atalhos navegaveis por teclado sem mouse (teste manual + axe-core)
- batch rejeita item sensivel (teste unitario)

**FAILURE MODES:**
1. Batch aprovando sensivel por bug -> teste unitario bloqueante.
2. Atalho `ENTER` disparar em campo de texto -> `event.target.matches('input, textarea')` guard.
3. Command palette pisando em `data-action` do shell ([front-end-dashboard-action-contract-map.md](../map/front-end-dashboard-action-contract-map.md)) -> namespace `data-wod-command` distinto.

**ROLLBACK:** feature-flag `FEATURE_WOD_INBOX_V2` em settings; fallback para template anterior.

---

### Onda 3 - Planner semanal (core)

**OBJETIVO:** criar a tela-mae de planejamento semanal com autonomia do OWNER.

**CONTRATO DE ENTRADA:** Ondas 0-2 merged. Feature-flag `FEATURE_WOD_PLANNER` criada.

**CONTRATO DE SAIDA:**
1. Rota `/operacao/wod/planner/` servindo grade 7xN.
2. Dataclasses `PlannerWeek`, `PlannerDay`, `PlannerCell` como contrato puro.
3. `WorkoutEditorHomeView` vira redirect 302 para `planner/`.

**PRS:**

**PR 3.1 - Contrato de leitura**
- CRIADO: `operations/workout_planner_context.py` - montagem de contexto da tela, consome builders
- CRIADO: `operations/workout_planner_builders.py` - agregacao pura por semana/slot, zero `request`
- CRIADO: `operations/workout_planner_presenter.py` - dataclasses `PlannerWeek`, `PlannerDay`, `PlannerCell` com `state: Literal['empty','draft','pending','published','sensitive']`
- TESTE: `tests/test_workout_planner_builders.py` cobrindo semana vazia, semana cheia, sensivel, rascunho

**PR 3.2 - View + template + CSS**
- CRIADO: `WorkoutPlannerView` em [operations/workspace_views.py](../../operations/workspace_views.py) (casca fina <= 30 linhas)
- CRIADO: `templates/operations/workout_planner.html`
- CRIADO: [static/css/design-system/operations/workspace/wod-planner.css](../../static/css/design-system/operations/workspace/wod-planner.css) usando `--wod-state-*` tokens
- CRIADO: [static/js/operations/wod_planner.js](../../static/js/operations/wod_planner.js) com navegacao por teclado
- CRIADO: [static/css/design-system/operations/workspace/wod-drawer.css](../../static/css/design-system/operations/workspace/wod-drawer.css) (historico como drawer)
- ALTERADO: [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css) adicionando tokens `--wod-state-*` e `--wod-cell-min-size`
- ALTERADO: [operations/urls.py](../../operations/urls.py) adicionando `operacao/wod/planner/` e fazendo `operacao/wod/editor/` virar redirect

**PR 3.3 - Acoes de celula**
- CRIADO: `operations/actions/workout_planner_actions.py` com `duplicate_previous_week`, `apply_template`, `assign_coach`
- CRIADO: `WorkoutPlannerCellActionView` em [operations/workout_action_views.py](../../operations/workout_action_views.py)
- ALTERADO: [operations/permissions.py](../../operations/permissions.py) garantindo que so OWNER/MANAGER acessa essas acoes
- ALTERADO: [operations/urls.py](../../operations/urls.py) com `operacao/wod/planner/celula/<int:session_id>/<str:action>/`
- TESTE: `tests/test_workout_planner_actions.py`

**DoD:**
- feature-flag por box operante; default OFF
- em box com flag ON, OWNER navega semana-a-semana com teclado
- duplicar semana anterior gera `SessionWorkout` clonado para os mesmos slots
- render p95 <= 400 ms
- A11y: grade com `role="grid"`, celulas com `role="gridcell"`, `aria-selected`, `aria-label` com estado
- telemetria `wod_planner_render_ms`, `wod_planner_action_key` emitida

**FAILURE MODES:**
1. Clonar semana e gerar duplicata em slot que ja tem WOD pendente -> query defensiva + mensagem explicita.
2. Duplicar WOD arrastando revisoes antigas -> ver [coach-wod-approval-corda.md](coach-wod-approval-corda.md) secao "duplicacao nao pode copiar trilha de aprovacao antiga".
3. Permissao frouxa -> teste por papel obrigatorio.
4. N+1 na grade -> `select_related('session', 'session__coach')` + `prefetch_related('blocks__movements')` com assert em teste.

**ROLLBACK:** `FEATURE_WOD_PLANNER=False` por box; redirect mantem rota viva via legado.

---

### Onda 4 - Editor COACH enxuto + ponte RM

**OBJETIVO:** coach publica WOD em <= 3 cliques com preview de carga.

**CONTRATO DE ENTRADA:** Onda 3 estabilizada em pelo menos 1 box.

**CONTRATO DE SAIDA:**
1. Editor abre pre-populado com "ontem+1".
2. Autocomplete de movimento resolve `movement_slug` sem digitacao.
3. Preview de prescricao em tempo real ao lado do campo de percentual.
4. CTA unico definido por `Box.wod_approval_policy`.

**PRS:**

**PR 4.1 - Autocomplete + catalogo**
- CRIADO: endpoint JSON `operations/workout_movement_catalog_view.py` retornando `[{slug, label, has_rm_data}]` por box
- ALTERADO: [operations/workout_editor_context.py](../../operations/workout_editor_context.py) expondo catalogo na montagem do editor
- CRIADO: [static/js/operations/wod_movement_autocomplete.js](../../static/js/operations/wod_movement_autocomplete.js)
- ALTERADO: [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html) com campo autocomplete

**PR 4.2 - Preview de prescricao**
- CRIADO: `operations/workout_prescription_preview.py` que usa [student_app/domain/workout_prescription.py](../../student_app/domain/workout_prescription.py) e agrega por aluno da aula
- CRIADO: endpoint JSON `operations/workout_prescription_preview_view.py`
- CRIADO: [static/js/operations/wod_prescription_preview.js](../../static/js/operations/wod_prescription_preview.js) com debounce 250 ms
- CRIADO: [static/css/design-system/operations/workspace/wod-editor.css](../../static/css/design-system/operations/workspace/wod-editor.css) (substitui parte de `coach-wod-*`)
- ALTERADO: [templates/operations/coach_session_workout_editor.html](../../templates/operations/coach_session_workout_editor.html) com painel "RM da aula"

**PR 4.3 - Duplicar slot anterior + politica**
- CRIADO: helper `clone_previous_slot_snapshot` em [operations/workout_support.py](../../operations/workout_support.py)
- ALTERADO: `CoachSessionWorkoutEditorView` em [operations/workspace_views.py](../../operations/workspace_views.py) para pre-popular via helper quando parametro `from=previous` ou editor novo
- CRIADO: migracao `boxes/migrations/XXXX_box_wod_approval_policy.py` com campo `wod_approval_policy` default `strict` (zero-downtime)
- CRIADO: metodo `SessionWorkout.should_require_approval(coach, source)` em [student_app/models.py](../../student_app/models.py) ou em `operations/workout_support.py` (preferir support para nao tocar models)
- ALTERADO: template do editor com CTA unico

**DoD:**
- em box com politica `trusted_template`, WOD aplicado de template com `is_trusted=True` publica direto
- preview de prescricao atualiza em <= 300 ms apos mudanca de %
- autocomplete devolve no max 50 itens e e keyboard-navigable
- testes em `tests/test_coach_wod_editor.py` cobrindo os 3 modos de politica

**FAILURE MODES:**
1. `should_require_approval` com logica frouxa abrindo bypass acidental -> teste exaustivo por politica + papel.
2. Catalogo de movimentos expondo dado de outro box -> filtro por `box_id` obrigatorio + teste de isolamento multi-tenant.
3. Preview chamando backend a cada keystroke -> debounce + cache no lado do cliente.
4. RM ausente quebrar preview -> fallback "N alunos sem RM" com link para quick-edit existente.

**ROLLBACK:** `FEATURE_WOD_EDITOR_V2` por box; autocomplete/preview degradam para campos simples.

---

### Onda 5 - Historico como drawer + estrangulador

**OBJETIVO:** remover superficie standalone do historico sem perder dado.

**CONTRATO DE ENTRADA:** Planner rodando em >= 80% dos boxes ativos.

**CONTRATO DE SAIDA:**
1. Historico consumido via drawer no Planner.
2. Rota `/operacao/wod/historico/` redireciona 302 para `planner/?drawer=history`.
3. Templates e includes standalone removidos.

**ARQUIVOS REMOVIDOS:**
- [templates/operations/workout_publication_history.html](../../templates/operations/workout_publication_history.html)
- [templates/operations/includes/wod_publication_history_content.html](../../templates/operations/includes/wod_publication_history_content.html)
- [templates/operations/includes/wod_publication_history_filters.html](../../templates/operations/includes/wod_publication_history_filters.html)

**MANTIDOS (contrato intacto):**
- [operations/workout_published_history.py](../../operations/workout_published_history.py)
- `WorkoutPublicationHistoryView` em [operations/workspace_views.py](../../operations/workspace_views.py) (serve markup do drawer)

**ALTERADOS:**
- [operations/urls.py](../../operations/urls.py) fazendo `operacao/wod/historico/` virar redirect
- [templates/operations/workout_planner.html](../../templates/operations/workout_planner.html) montando o drawer
- [static/css/design-system/operations/workspace/wod-drawer.css](../../static/css/design-system/operations/workspace/wod-drawer.css) expandido

**DoD:**
- nenhum link quebrado nos emails e notificacoes existentes (grep por `/operacao/wod/historico/`)
- drawer acessivel por teclado (`Esc` fecha, focus trap)
- testes em `tests/test_workout_post_publication_history.py` passando sem alteracao de contrato

**FAILURE MODES:**
1. Remover include ainda referenciado por outro template -> grep obrigatorio antes do delete.
2. Drawer quebrando scroll do Planner -> `overflow: hidden` no body quando drawer aberto, via `data-wod-drawer-open`.

**ROLLBACK:** revert dos deletes + remover redirect; rota volta a servir template standalone.

---

### Onda 6 - WorkoutTemplate

**OBJETIVO:** OWNER aplica template em celula com 1 clique.

**CONTRATO DE ENTRADA:** Ondas 3 e 4 merged.

**CONTRATO DE SAIDA:**
1. `WorkoutTemplate`, `WorkoutTemplateBlock`, `WorkoutTemplateMovement` em novo app ou em `operations/` conforme decisao abaixo.
2. CRUD minimo do OWNER.
3. Acao `apply_template` disponivel na celula do Planner.

**DECISAO DE OWNERSHIP:**
- Criar em `operations/workout_templates.py` (domain) + `operations/models.py` se operations ja possuir models, senao criar `operations/template_models.py` minimalista.
- **Nao** tocar em `student_app/models.py`.

**ARQUIVOS CRIADOS:**
- `operations/workout_templates.py` (domain + services)
- `operations/migrations/XXXX_workout_template.py`
- `operations/workout_template_actions.py` (aplicar template)
- `operations/forms.py` extendido com `WorkoutTemplateForm`
- `templates/operations/includes/wod_template_picker.html`
- `templates/operations/workout_template_crud.html` (OWNER-only)
- `tests/test_workout_template.py`

**ALTERADOS:**
- [operations/urls.py](../../operations/urls.py) com CRUD em `operacao/wod/templates/`
- [operations/workout_action_views.py](../../operations/workout_action_views.py) expondo `apply_template_to_session`

**DoD:**
- OWNER cria template em <= 60 s
- aplicar template em celula vazia gera WOD valido em <= 500 ms
- template `is_trusted=True` respeita politica do box (`trusted_template` publica direto)
- zero migracao em `SessionWorkout*`

**FAILURE MODES:**
1. Template com movimento sem RM cadastrado no box -> aviso visual, nao erro.
2. Aplicar template em celula ja com WOD -> modal de confirmacao obrigatorio.
3. Template compartilhado entre boxes por bug -> filtro `box_id` em todo query + teste multi-tenant.

**ROLLBACK:** `FEATURE_WOD_TEMPLATES=False`; migracao reversivel (tabela nova, sem FK quebravel).

---

### Onda 7 - Limpeza CSS + consolidacao de tokens

**OBJETIVO:** reduzir CSS do corredor WOD >= 30% e deixar tokens canonicos.

**CONTRATO DE ENTRADA:** Ondas 1-6 merged e estaveis por >= 2 semanas.

**CONTRATO DE SAIDA:**
1. Classes `coach-wod-*` orfas removidas.
2. Componentes consumindo apenas tokens de [tokens.css](../../static/css/design-system/tokens.css).
3. Zero `!important` novo.
4. Registro de assets via `build_catalog_assets`.

**METODOLOGIA:**
1. Rodar `py .agents/skills/octobox-ui-cleanup-auditor/scripts/frontend_forensics.py` novamente.
2. Cruzar com a taxonomia `dead`/`candidate-unused`/`legacy-bridge` (ver [referencia de auditoria](../../.agents/skills/octobox-ui-cleanup-auditor/references/finding-taxonomy.md)).
3. Para cada classe marcada `dead`, grep em templates + JS + payloads antes de remover.
4. Proteger aliases canonizados (`note-panel*`, `legacy-copy*`) conforme guardrail.

**ARQUIVOS ALTERADOS:**
- [static/css/design-system/operations/dev-coach/coach.css](../../static/css/design-system/operations/dev-coach/coach.css) (enxugado)
- [static/css/design-system/tokens.css](../../static/css/design-system/tokens.css) (tokens `--wod-*` consolidados)

**DoD:**
- `wc -l` do `coach.css` cai >= 30%
- `grep -r "!important" static/css/design-system/operations/workspace/wod-*` = 0
- lighthouse Performance das tres telas >= 90
- zero regressao visual em snapshot manual

**FAILURE MODES:**
1. Remover classe ainda usada por payload Python -> grep obrigatorio em `*.py` tambem.
2. Tocar classes `note-panel*` ou `legacy-copy*` -> guardrail auditor.

**ROLLBACK:** revert do PR; sem dado envolvido.

---

## Mapa consolidado de arquivos

### Criados

```
docs/plans/wod-ui-ux-revolution-wave0-inventory.md
operations/workout_planner_context.py
operations/workout_planner_builders.py
operations/workout_planner_presenter.py
operations/workout_movement_catalog_view.py
operations/workout_prescription_preview.py
operations/workout_prescription_preview_view.py
operations/workout_templates.py
operations/workout_template_actions.py
operations/actions/workout_planner_actions.py
operations/actions/workout_batch_approval.py
operations/migrations/XXXX_workout_template.py
boxes/migrations/XXXX_box_wod_approval_policy.py
templates/operations/workout_planner.html
templates/operations/workout_template_crud.html
templates/operations/includes/wod_command_palette.html
templates/operations/includes/wod_template_picker.html
templates/operations/includes/wod_tooltip.html
static/css/design-system/operations/workspace/wod-planner.css
static/css/design-system/operations/workspace/wod-inbox.css
static/css/design-system/operations/workspace/wod-drawer.css
static/css/design-system/operations/workspace/wod-editor.css
static/css/design-system/operations/workspace/wod-command-palette.css
static/js/operations/wod_planner.js
static/js/operations/wod_inbox.js
static/js/operations/wod_command_palette.js
static/js/operations/wod_movement_autocomplete.js
static/js/operations/wod_prescription_preview.js
tests/test_workout_planner_builders.py
tests/test_workout_planner_actions.py
tests/test_workout_template.py
```

### Alterados

```
operations/workspace_views.py                       (+ WorkoutPlannerView, - WorkoutEditorHomeView)
operations/urls.py                                   (+ planner, + batch, + celula, + templates, redirects)
operations/workout_action_views.py                   (+ batch, + planner cell, + apply template)
operations/workout_approval_board_context.py         (+ inbox items)
operations/workout_editor_context.py                 (+ catalogo de movimentos)
operations/workout_support.py                        (+ clone_previous_slot_snapshot, + should_require_approval)
operations/permissions.py                            (+ guards de planner actions)
operations/forms.py                                  (+ WorkoutTemplateForm)
templates/operations/workout_approval_board.html     (silencio + inbox)
templates/operations/coach_session_workout_editor.html (autocomplete + preview + CTA unico)
templates/operations/includes/wod_corridor_tabs.html  (enxuto)
static/css/design-system/tokens.css                  (+ tokens --wod-*)
static/css/design-system/operations/dev-coach/coach.css (- classes orfas)
```

### Removidos (ao final)

```
templates/operations/workout_editor_home.html
templates/operations/workout_publication_history.html
templates/operations/includes/wod_publication_history_content.html
templates/operations/includes/wod_publication_history_filters.html
WorkoutEditorHomeView em operations/workspace_views.py
```

---

## Contratos tecnicos explicitos

### Dataclass `PlannerCell`

```python
@dataclass(frozen=True, slots=True)
class PlannerCell:
    session_id: int
    scheduled_at: datetime
    slot_label: str
    coach_label: str
    workout_id: int | None
    state: Literal['empty', 'draft', 'pending', 'published', 'sensitive']
    is_sensitive: bool
    is_sensitive_diff: bool
    available_actions: tuple[str, ...]
    href_editor: str
    href_preview: str
```

### Metodo `SessionWorkout.should_require_approval`

```python
def should_require_approval(self, *, coach, source: Literal['manual','template','duplicate']) -> bool:
    policy = self.session.box.wod_approval_policy
    if policy == 'strict':
        return True
    if policy == 'trusted_template' and source == 'template' and self.source_template and self.source_template.is_trusted:
        return False
    if policy == 'coach_autonomy' and getattr(coach, 'is_trusted_author', False):
        return False
    return True
```

(Implementar como funcao em `operations/workout_support.py` e expor via metodo conveniente; **nao** colocar logica de policy no model se puder evitar.)

### Atalhos de teclado (contrato de UI)

| Tecla | Contexto | Acao |
|---|---|---|
| `j`/`k` | Inbox | navegar item anterior/proximo |
| `ENTER` | Inbox com foco em item nao-sensivel | aprovar |
| `Ctrl+K` | Qualquer tela WOD | abrir command palette |
| `setas` | Planner | mover foco de celula |
| `ENTER` | Planner celula | abrir editor |
| `Ctrl+D` | Planner celula | duplicar WOD do slot anterior |
| `Esc` | Drawer/palette aberto | fechar |

### Tokens CSS canonicos (adicionar)

```css
:root {
    --wod-state-empty: var(--color-surface-subtle);
    --wod-state-draft: var(--color-warning-subtle);
    --wod-state-pending: var(--color-info);
    --wod-state-published: var(--color-success);
    --wod-state-sensitive: var(--color-danger);
    --wod-cell-min-size: 72px;
    --wod-planner-gap: var(--space-1);
    --wod-drawer-width: 420px;
    --wod-inbox-list-width: 360px;
}
```

(Mapear os `--color-*` para tokens ja existentes em [tokens.css](../../static/css/design-system/tokens.css); **nao** criar cores novas.)

---

## Traceability papel -> acao -> arquivo

| Papel | Acao | Endpoint | View | Context/Builder | Template | CSS | JS | Teste |
|---|---|---|---|---|---|---|---|---|
| OWNER | Ver mes | GET `/operacao/wod/planner/?scope=month` | `WorkoutPlannerView` | `workout_planner_context.py` + `workout_planner_builders.py` | `workout_planner.html` | `wod-planner.css` | `wod_planner.js` | `tests/test_workout_planner_builders.py` |
| OWNER | Duplicar semana | POST `/operacao/wod/planner/duplicar-semana/` | `WorkoutPlannerCellActionView` | `actions/workout_planner_actions.py` | - | - | - | `tests/test_workout_planner_actions.py` |
| OWNER | Aplicar template | POST `/operacao/wod/planner/celula/<id>/apply-template/` | `WorkoutPlannerCellActionView` | `workout_template_actions.py` | `includes/wod_template_picker.html` | - | - | `tests/test_workout_template.py` |
| OWNER | Publicar em lote | POST `/operacao/wod/aprovacoes/lote/` | `WorkoutApprovalBatchActionView` | `actions/workout_batch_approval.py` | - | - | `wod_command_palette.js` | `tests/test_workout_approval_board.py` |
| MANAGER | Aprovar item | POST `/operacao/wod/<id>/approve/` | `WorkoutApprovalActionView` (existente) | `workout_support.py` | `workout_approval_board.html` | `wod-inbox.css` | `wod_inbox.js` | `tests/test_workout_approval_board.py` |
| MANAGER | Rejeitar | POST `/operacao/wod/<id>/reject/` | `WorkoutApprovalActionView` (existente) | existente | existente | `wod-inbox.css` | `wod_command_palette.js` | existente |
| COACH | Criar WOD autocomplete | GET `/operacao/wod/movimentos/?box=<id>` | `WorkoutMovementCatalogView` | `workout_editor_context.py` | - | - | `wod_movement_autocomplete.js` | `tests/test_coach_wod_editor.py` |
| COACH | Preview prescricao | GET `/operacao/wod/preview-prescricao/` | `WorkoutPrescriptionPreviewView` | `workout_prescription_preview.py` | - | `wod-editor.css` | `wod_prescription_preview.js` | `tests/test_coach_wod_editor.py` |
| COACH | Publicar (politica) | POST `/operacao/coach/aula/<id>/wod/publish/` | `CoachSessionWorkoutEditorView` | `workout_support.should_require_approval` | `coach_session_workout_editor.html` | `wod-editor.css` | - | `tests/test_coach_wod_editor.py` |

---

## Feature-flag strategy

1. Flags em `Box.feature_flags` (JSONField) ou em `settings` por ambiente, seguindo padrao existente do repo. **Confirmar em Onda 0.**
2. Flags propostas:
   - `FEATURE_WOD_INBOX_V2` (Onda 2)
   - `FEATURE_WOD_PLANNER` (Onda 3)
   - `FEATURE_WOD_EDITOR_V2` (Onda 4)
   - `FEATURE_WOD_TEMPLATES` (Onda 6)
3. Default OFF; ON progressivo por piloto (1 box -> 5 -> 20 -> geral).
4. Telemetria por flag: `wod_planner_render_ms{flag=on|off}`.

---

## Observabilidade

Emitir via structlog (padrao existente) em todas as ondas:

| Evento | Atributos | Onda |
|---|---|---|
| `wod_action_duration_ms` | `action, workout_id, user_id, duration_ms` | 0 |
| `wod_inbox_keyboard_action` | `key, item_count` | 2 |
| `wod_batch_approval` | `approved_count, skipped_sensitive_count` | 2 |
| `wod_planner_render_ms` | `scope, week_iso, cell_count, duration_ms` | 3 |
| `wod_planner_action` | `action_key, cell_id, duration_ms` | 3 |
| `wod_prescription_preview_hit` | `movement_slug, student_count, has_rm_count` | 4 |
| `wod_template_applied` | `template_id, box_id, is_trusted, bypass_approval` | 6 |

Dashboard consolidado: Grafana/operacional existente (confirmar durante Onda 0).

---

## Seguranca e multi-tenant

1. Todo endpoint novo filtra por `box_id` do usuario atual.
2. Catalogo de movimentos **nao** pode vazar entre boxes (teste dedicado).
3. Template **nao** pode ser aplicado em sessao de outro box.
4. `batch_approve` valida papel em cada item (nao assume lote homogeneo).
5. Auditoria existente (`SessionWorkoutRevision`) continua gravando cada acao.

---

## O que NAO fazer agora (guardrails contra overengineering)

1. Nao introduzir framework JS (React/Vue/Alpine). Tudo com ES modules nativos.
2. Nao reescrever `SessionWorkout*` nem `StudentExerciseMax`.
3. Nao mover politica de aprovacao para o template (viola camadas).
4. Nao criar "plugin system" de templates.
5. Nao transformar command palette em fuzzy search global da app.
6. Nao misturar logica de heuristica com presenter.
7. Nao mexer em `note-panel*` ou `legacy-copy*` sem revisar [front-legacy-rule-retirement-sdd.md](front-legacy-rule-retirement-sdd.md).
8. Nao tocar no corredor `/aluno/`.

---

## Plano de validacao

Por onda:
1. testes unitarios novos passando
2. suite existente passando sem alteracao
3. `scripts/frontend_forensics.py` rodado e diff anexado ao PR
4. lighthouse A11y/Performance nas telas afetadas
5. teste manual em mobile (iOS Safari + Android Chrome) para ondas 2, 3, 4
6. amostragem de telemetria 48h em staging antes de ativar flag em producao

---

## Resumo infantil

Pense no corredor WOD como uma escola:

1. OWNER e o diretor - olha o calendario do ano inteiro e decide o que vai acontecer
2. MANAGER e o coordenador - confere o plano da semana e aprova aula por aula
3. COACH e o professor - escreve o treino do dia da sua aula

Hoje cada um tem um caderno diferente e eles quase nao conversam.

Com o Planner, todos abrem o **mesmo caderno**, so que cada um ve a pagina do seu tamanho:

1. diretor ve o mes
2. coordenador ve a semana
3. professor ve a aula

E quando o professor escreve "5 agachamentos com 70% do seu maximo", o app ja traduz pra cada aluno: "Joao, 72,5 kg. Maria, 55 kg."

Ninguem precisa fazer conta. Ninguem precisa adivinhar. Todo mundo ve o que precisa ver.
