# WOD Smart Paste — Plano Corda

## Problema

Coaches colam treinos semanais em texto livre (formato verbal PT-BR). Hoje precisam montar bloco a bloco no editor, para cada `ClassSession` individualmente. Não existe conceito de semana, tipo de aula explícito, ou replicação em massa.

## Objetivo

1. Canal de colagem inteligente: coach cola texto → sistema organiza em estrutura (semana × dia × blocos × movimentos).
2. Revisão visual antes de persistir.
3. 1 clique replica o plano semanal nas `ClassSession` elegíveis por tipo de aula e data.
4. Não quebrar o editor atual (9 intents, `SessionWorkout`, fluxo DRAFT → PUBLISHED).

---

## Arquitetura

### Novos modelos

```
WeeklyWodPlan
  id, box, created_by, week_start (date), label, created_at, status (DRAFT|CONFIRMED)

DayPlan
  id, weekly_plan FK, weekday (0=seg…6=dom), sort_order

PlanBlock
  id, day_plan FK, kind (warmup|skill|metcon|cooldown|mobility|custom)
  title, notes, timecap_min, rounds, interval_seconds, sort_order

PlanMovement
  id, plan_block FK, movement_slug, movement_label_raw
  sets, reps_spec, load_spec, notes, sort_order

ReplicationBatch
  id, weekly_plan FK, created_by, created_at, class_type_filter (JSON)
  sessions_targeted (int), sessions_created (int), undone_at (nullable)
```

### Não altera

`SessionWorkout`, `SessionWorkoutBlock`, `SessionWorkoutMovement` — o motor de projeção **cria** registros nesses models existentes como DRAFT. O editor atual permanece intacto.

### ClassType (pré-requisito)

Adicionar `class_type` enum em `ClassSession`:

```python
class ClassType(models.TextChoices):
    CROSS    = "cross",    "CrossFit"
    MOBILITY = "mobility", "Mobilidade / Alongamento"
    OLY      = "oly",      "Halterofilia"
    STRENGTH = "strength", "Força"
    OPEN_GYM = "open_gym", "Open Gym"
    OTHER    = "other",    "Outro"
```

Backfill por regra de título (case-insensitive): "cross" → CROSS, "mobilidade|alongamento" → MOBILITY, etc. Revisão manual antes de ativar replicação.

### Regra de compatibilidade bloco × aula

| ClassType | Blocos aceitos |
|---|---|
| cross | todos |
| mobility | warmup, mobility, cooldown |
| oly | warmup, skill, cooldown |
| strength | warmup, skill, cooldown |
| open_gym | todos |
| other | todos |

Projeção **descarta** blocos incompatíveis com aviso visível no preview — nunca silenciosamente.

---

## Parser (L1 + L2)

### L1 — Heurística determinística PT-BR (`wod_paste_parser.py`)

**Tokenização em fases:**

1. **Fase 1 — Cabeçalho de dia**: `^(Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)` inicia novo `DayPlan`.
2. **Fase 2 — Cabeçalho de bloco**: palavras-chave case-insensitive:
   - `Mobilidade` → `mobility`
   - `Aquecimento` → `warmup`
   - `Skill` → `skill`
   - `Wod` → `metcon`
   - `Cooldown|Descanso ativo` → `cooldown`
3. **Fase 3 — Metadados de bloco**: regex extraindo:
   - Timecap: `(\d+)m` antes de movimento → `timecap_min`
   - Rounds: `(\d+)x|(\d+) rounds?` → `rounds`
   - Intervalo: `Emom (\d+)m` → `interval_seconds = 60`, `rounds = N`
   - Score type: `Amrap`, `For time`, `21/15/9` (piramidal)
4. **Fase 4 — Movimentos**: cada linha restante tenta match no dicionário (`wod-movement-dictionary.md`). Extrai `reps_spec` e `load_spec` por regex: `(\d+/\d+|\d+)\s+(.+?)(\s+[\d.]+/[\d.]+kg?)?$`.
5. **Linhas não resolvidas**: marcadas `{line, text, error}` — **não descartadas**.

### L2 — Fallback LLM (Haiku 4.5)

Ativado somente se L1 deixar linhas não resolvidas ou o bloco do dia ficar vazio.

- Input: linhas não resolvidas + contexto do bloco pai.
- Output: JSON contra `wod-paste-schema.md`.
- Slug só aceito se constar no dicionário; caso contrário, retorna `movement_slug: null`, `movement_label_raw: <texto>` para revisão humana.
- Prompt cacheado: system + schema + dicionário (estático). Único input dinâmico: as linhas problemáticas.
- Modelo: `claude-haiku-4-5-20251001` (barato, <1s para extração estruturada).

---

## Restrição de inicio de semana — segunda-feira obrigatória

`WeeklyWodPlan.week_start` e `target_week_start` da projeção aceitam apenas segunda-feira.

**Client-side (snap automático):**
- JS em `static/js/operations/smart_paste_week_monday.js` intercepta change/blur nos campos `[data-smart-date-monday-wrap]`.
- Se o dia selecionado nao for segunda (JS `getDay() !== 1`), recua para a segunda anterior via `prevMonday()`.
- Exibe hint `[data-smart-date-monday-hint]` com texto "Ajustado para segunda dd/mm" via `aria-live="polite"`.
- O campo texto (`dd/mm`) e o picker nativo (`<input type=date step=7>`) sao atualizados em sincronia.

**Server-side (validação em `forms.py`):**
- `_coerce_smart_paste_date` ja retorna `date`; adicionar guard pos-parse:
  ```python
  if candidate.weekday() != 0:
      candidate = candidate - timedelta(days=candidate.weekday())
  ```
  Snap server-side espelha o client para garantir consistência sem duplo erro.

**Include unificado:**
- `templates/operations/includes/wod_smart_paste_week_input.html` substitui os dois blocos inline de data (em `workout_smart_paste.html` e `wod_smart_paste_projection.html`).
- Parâmetros: `field`, `picker_id`, `picker_value`, `label_text`.

---

## UI — Stepper 3 passos

### Passo 1 — Colar

```
┌─────────────────────────────────────────┐
│  Cole o treino da semana aqui           │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  ← textarea monospace grande
│  Segunda                                │
│  Mobilidade                             │
│  Aquecimento                            │
│  3x                                     │
│  ...                                    │
│                                         │
│              [Organizar →]              │
└─────────────────────────────────────────┘
```

- Autosave rascunho (localStorage + servidor como `WeeklyWodPlan` DRAFT).
- Placeholder mostra formato aceito com exemplo mínimo.
- Sem validação client-side — servidor devolve erros.

### Passo 2 — Conferir

Grid 7 colunas (seg–dom) × linhas de blocos.

```
SEG          TER          QUA      ...
─────────────────────────────────────
[Mobilidade] [Mobilidade] [Mobili.]
[Aquec. 3x]  [Aquec. 3x]  [Aquec.]
  10 lunges    10 push up   5 p snatch ⚠ revisar
  8 front sq   8 sho press  5 ohs
  20 sit up    100 run      5 s bala.. ⚠ revisar
[Skill]       [Emom 20m]   [Skill]
  Semana 2     A 6 push jk  6 rounds
  7×65%        B 10-12 t2b  1 p snat
  7 back sq    C 5 H clean  1 sqt sn
               D 2 RC
               E rest
[Wod 10m]    [Wod 14m]    [Wod 14m]
  21/15/9      100 push up  1.200 run
  Thruster     50 push pr   60 bjo
  Pull up      400 run      40 wall b
  3 BOB/quebra              15 bmu
```

- Itens `⚠ revisar`: borda tracejada `--color-warning`, clique abre inline-edit.
- Inline-edit: input text + dropdown de slug canônico. Não modal.
- Botão "← Corrigir texto" volta ao passo 1 preservando edições manuais do passo 2.

### Passo 3 — Replicar

```
Semana alvo:  [◀ 21 abr–27 abr ▶]

Tipos de aula:
  ☑ CrossFit (cross)         → 5 aulas encontradas
  ☑ Mobilidade               → 3 aulas encontradas  [blocos descartados: Wod, Skill]
  ☐ Halterofilia             → 0 aulas nesta semana
  ☐ Open Gym

Preview do que será criado:
  18 WODs em DRAFT (revisão necessária antes de publicar)
  3 WODs com blocos descartados (incompatíveis com tipo de aula)

[Cancelar]                [Criar WODs em DRAFT →]
```

- Rascunho semanal persiste; sair e voltar retoma exatamente onde estava.
- Após confirmar: banner "18 WODs criados — [Desfazer] (disponível por 24h)".
- Desfazer = cancela todos os DRAFTs do `ReplicationBatch` que ainda não foram publicados.

---

## Waves de entrega

| Wave | Entregável | Critério de done | Risco |
|---|---|---|---|
| 0 | Este doc + `wod-movement-dictionary.md` + `wod-paste-schema.md` | Aprovados pelo tech lead | — |
| 1 | `ClassType` enum + migração + backfill | Testes de migração passam; backfill revisado manualmente por 1 box piloto | Baixo |
| 2 | `WeeklyWodPlan`, `DayPlan`, `PlanBlock`, `PlanMovement`, `ReplicationBatch` (models only, sem UI) | Migrations geradas; admin Django funcional para inspeção | Baixo |
| 3 | Parser L1 (`wod_paste_parser.py`) + testes unitários com fixture do exemplo real | 100% das linhas do exemplo da semana na spec parseadas sem L2 | Médio |
| 4 | UI stepper passo 1 + 2 (sem replicação) | Coach cola texto, vê preview, edita inline, confirma | Médio |
| 5 | Motor de projeção + UI passo 3 (replicar) | WODs DRAFT criados corretamente por ClassType; desfazer funciona | Alto |
| 6 | Parser L2 (LLM Haiku) atrás de feature flag | Flag desabilitada por default; ativa por box no admin | Alto (LLM) |

---

## Fixture de referência (exemplo real do usuário)

O texto abaixo **é a fixture de teste para o parser L1**. Qualquer build deve parsear este input sem recorrer a L2.

```
Segunda
Mobilidade

Aquecimento
3x
10 lunges
8 front squat
20 sit up

Skill
Semana 2
7 rounds 65%
7 back squat

Wod
10m
21/15/9

Thruster
Pull up

Cada quebra 3 BOB

Terça

Mobilidade

Aquecimento
3x
10 push up
8 shoulder press
100 run

Skill
Emom 20m
A 6 push jerk
B 10 a 12 t2b
C 5 Hang clean
D 2 RC
E rest

Wod  14m
100 push up
50 push press  40/25
400 run

Quarta
Mobilidade

Aquecimento
3x
5 power snatch
5 ohs
5 s balance

Skill
6 rounds

1 p snatch
1 squat snatch

Wod  14m
1.200 run
60 bjo
40 wall ball
15 bmu / 25 pull up

Quinta
Mobilidade
Aquecimento
3x
20 kbs A
12 v up
30 du

Skill
Semana 2

7 rounds 70%
5 deadlift

Wod
Amrap 16m

Duplas um round para cada
15 t2b
10 deadlift
15 strict hspu

Sexta
Mobilidade

Aquecimento
3x
10 Hollow rock
8 front squat
5 strict t2b
5 strict pull up

Skill

A cada 30s por 15 x
1 squat clean + 1 Hang squat clean

Wod  15m
5 rounds

12 front squat
9 Hang clean
6 S2OH
30 du
```

---

## Arquivos a criar/alterar

| Arquivo | Ação |
|---|---|
| `operations/models/weekly_wod_plan.py` | Criar — novos models |
| `operations/models/__init__.py` | Adicionar exports |
| `operations/services/wod_paste_parser.py` | Criar — parser L1 + L2 |
| `operations/services/wod_projection.py` | Criar — motor de projeção |
| `operations/views/wod_smart_paste_views.py` | Criar — views do stepper |
| `operations/templates/operations/wod_smart_paste/` | Criar — 3 templates parciais |
| `operations/urls.py` | Adicionar rota `wod/paste/` |
| `operations/models/class_session.py` | Adicionar `class_type` field |
| `docs/reference/wod-movement-dictionary.md` | Criar |
| `docs/reference/wod-paste-schema.md` | Criar |

---

## Decisões registradas

- **L2 atrás de feature flag**: evita dependência de LLM no caminho crítico. L1 resolve >95% dos casos reais.
- **WeeklyWodPlan não substitui SessionWorkout**: projeção alimenta o editor existente. Sem ruptura de contrato (doc `coach-session-workout-editor-wave0-inventory.md`).
- **ClassType obrigatório antes da replicação**: sem type explícito, replicação está desabilitada. Backfill não é suficiente — revisão humana required.
- **Desfazer limitado a 24h e DRAFT-only**: WODs publicados não são afetados. Sem rollback de aprovações.
