<!--
ARQUIVO: especificacao do SmartPlan — fluxo de normalizacao de WOD via GPT customizado e tier de exibicao bifurcado.

POR QUE ELE EXISTE:
- formaliza a decisao de produto de bifurcar a exibicao do WOD em dois tiers (cru e detalhado) para criar incentivo natural de qualidade.
- registra a integracao com app GPT proprio como caminho BYOLLM, sem custo de API para o OctoBOX.
- consolida as decisoes de arquitetura, design system e UX que governam essa feature.

O QUE ESTE ARQUIVO FAZ:
1. descreve o fluxo SmartPlan ponta a ponta.
2. define o gating UX (popup de aviso) e a regra de bifurcacao de render.
3. especifica MovementLibrary, integracao com crossfit.com e vinculo com RM do aluno.
4. desdobra a implementacao em ondas atomicas.

TIPO DE DOCUMENTO:
- spec de produto + plano de implementacao em ondas

AUTORIDADE:
- alta para o escopo de normalizacao de WOD e tier de exibicao

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

DOCUMENTO PREDECESSOR:
- [wod-smart-paste-corda.md](wod-smart-paste-corda.md) — colagem com parser local; SmartPlan herda os modelos `WeeklyWodPlan`, `DayPlan`, `PlanBlock`, `PlanMovement` ja em runtime e adiciona o caminho BYOLLM e o tier de exibicao.

QUANDO USAR:
- quando houver duvida sobre o que e SmartPlan, qual a regra de tier ou como integrar com o GPT customizado.
- quando uma feature nova depender de saber se o WOD e cru ou detalhado.

PONTOS CRITICOS:
- texto cru nao bloqueia publicacao; bloqueio e psicologico via popup, nao tecnico.
- normalizacao acontece fora do servidor OctoBOX (BYOLLM); o servidor so valida e parsea o output colado.
- MovementLibrary e ativo curado pela OctoBOX; coach nao edita.
- crossfit.com e fonte canonica de demonstracao; nao reproduzir conteudo, apenas linkar.
-->

# SmartPlan — Normalizacao de WOD e Tier Bifurcado

## Documentos canonicos consultados

Este plano respeita a hierarquia de [documentation-authority-map.md](../map/documentation-authority-map.md). As decisoes deste documento sao subordinadas a:

1. [octobox-architecture-model.md](../architecture/octobox-architecture-model.md) — modelo do predio e regra de leitura.
2. [domain-model-ownership-matrix.md](../architecture/domain-model-ownership-matrix.md) — onde cada modelo deve nascer e o pattern `model_definitions.py -> models.py`.
3. [themeOctoBox.md](../architecture/themeOctoBox.md) — tema visual oficial; precede qualquer decisao de paleta, sombra ou glow.
4. [design-system-contract.md](../map/design-system-contract.md) — contrato curto de ownership do CSS.
5. [css-guide.md](../experience/css-guide.md) — guia operacional de CSS, hosts canonicos e camada de variantes.
6. [architecture-growth-plan.md](../architecture/architecture-growth-plan.md) — direcao macro de evolucao; SmartPlan se encaixa na fase de integracoes externas + jobs.
7. [wod-smart-paste-corda.md](wod-smart-paste-corda.md) — predecessor que ja entregou os modelos de plano semanal usados aqui.

Em caso de conflito entre este plano e qualquer doc da lista acima, vence o doc da lista.

## Tese de produto

O OctoBOX **nao forca** o coach a normalizar. Ele **recompensa** quem normaliza com um app do aluno mais rico. A pressao por qualidade vem do aluno, nao do sistema.

Em duas frases:

1. Coach que escreve cru → aluno ve texto simples; vida segue.
2. Coach que normaliza pelo SmartPlan → aluno ve videos, metricas, vinculo de RM, deteccao de PR; aluno engaja mais; box retem mais.

## O fluxo SmartPlan ponta a ponta

```
[1] Coach ou Owner abre editor de WOD em operations/wod/editor/
        |
        v
[2] No topo do editor: card SmartPlan com botao
    "Abrir SmartPlan no ChatGPT"
        |
        v
[3] Click abre em nova aba o GPT customizado da OctoBOX
    (URL fixa do GPT publico)
        |
        v
[4] Coach cola o WOD bruto no GPT
        |
        v
[5] GPT devolve em formato canonico (texto + JSON entre marcadores)
        |
        v
[6] Coach copia a resposta inteira e cola no editor do OctoBOX
        |
        v
[7] OctoBOX valida o input ao publicar:
        |
        +-- formato valido (marcadores OK + JSON parseavel)
        |       --> is_normalized=True, structured_payload preenchido
        |       --> publica com tier RICO no app do aluno
        |
        +-- formato invalido (texto cru sem marcadores)
                --> popup de aviso aparece
                --> [Voltar e formatar]   --> volta ao editor
                --> [Publicar mesmo assim] --> is_normalized=False
                                              publica com tier CRU
```

## Componentes do sistema

### 1. GPT customizado (fora do OctoBOX)

URL: a definir e fixar em `settings.SMARTPLAN_GPT_URL`.

Conteudo do GPT (instructions field do GPT editor):

1. especificacao de formato de saida (marcadores `=== WOD NORMALIZADO ===` e `=== JSON ESTRUTURADO ===`).
2. dicionario canonico de movimentos (referencia o crossfit.com).
3. regras invioláveis: nao inventar carga, nao inventar distancia, marcar ambiguidade com `[?]`.
4. principios de prescricao do CrossFit Affiliate Programming.
5. exemplos de input cru e output normalizado.

Esse GPT e **ativo da OctoBOX**, versionado em texto em `operations/services/wod_normalization/prompts/smartplan_v1.md` para documentacao interna.

### 2. Editor de WOD no OctoBOX

Localizacao real (validada contra runtime):
- view: `operations/workout_editor_views.py` (flat, sem subpasta `views/`)
- actions: `operations/workout_editor_actions.py`
- dispatcher: `operations/workout_editor_dispatcher.py` (despacha intents)
- template principal: `templates/operations/workout_editor_home.html`
- partials existentes do tipo wod: `templates/operations/includes/wod_*.html`

Modificacao:
- adiciona card SmartPlan no topo do `workout_editor_home.html` (ou novo include `templates/operations/includes/wod_smartplan_card.html`).
- card contem botao **"Abrir SmartPlan"** (link externo para `SMARTPLAN_GPT_URL`) e link auxiliar **"Como funciona?"** (abre modal).
- textarea de WOD continua igual.
- adiciona um intent novo no `workout_editor_dispatcher.py` para validacao do paste antes do publish.
- intent `publish` chama `detect_smartplan_format()` antes de salvar.

### 3. Validador de formato

Modulo: `operations/services/wod_normalization/response_parser.py`.

Funcao:
```python
def detect_smartplan_format(raw_text: str) -> dict:
    """Detecta se o texto colado segue formato SmartPlan."""
    has_text_marker = '=== WOD NORMALIZADO ===' in raw_text
    has_json_marker = '=== JSON ESTRUTURADO ===' in raw_text
    if not (has_text_marker and has_json_marker):
        return {'is_normalized': False, 'reason': 'markers_missing'}

    try:
        normalized_text = extract_section(raw_text, 'WOD NORMALIZADO')
        json_block = extract_section(raw_text, 'JSON ESTRUTURADO')
        structured = json.loads(strip_code_fence(json_block))
    except (ValueError, json.JSONDecodeError) as exc:
        return {'is_normalized': False, 'reason': 'parse_error', 'detail': str(exc)}

    return {
        'is_normalized': True,
        'normalized_text': normalized_text.strip(),
        'structured_payload': structured,
    }
```

Sem dependencia externa. Sem chamada de API. Apenas parsing local.

### 4. Popup de aviso

Disparado quando `detect_smartplan_format(...)['is_normalized'] == False`.

Conteudo:

```
┌──────────────────────────────────────────────┐
│  ⚠ WOD fora do formato SmartPlan             │
├──────────────────────────────────────────────┤
│                                              │
│  No app do aluno este WOD vai aparecer       │
│  apenas como texto cru. Voce perde:          │
│                                              │
│  ✗ Videos por movimento                      │
│  ✗ Vinculo automatico com o RM do aluno      │
│  ✗ Sugestao de carga e scaling               │
│  ✗ Deteccao automatica de PR                 │
│  ✗ Metricas de volume e progressao           │
│  ✗ Comparacao com WODs anteriores            │
│                                              │
│  [Voltar e formatar com SmartPlan]  ← primary │
│  [Publicar mesmo assim]             ← danger  │
└──────────────────────────────────────────────┘
```

Padrao visual: usar `notice-panel` host canonical com variant `--warning`. NAO criar componente novo.

### 5. Render bifurcado no app do aluno

#### Realidade validada contra runtime

`templates/student_app/wod.html` ja existe **como arquivo unico** e ja renderiza com tier rico (usa `student-card --feature` + itera `student_workout_day.blocks` que vem dos modelos relacionais `SessionWorkoutBlock` + `SessionWorkoutMovement`). View dona: `student_app/views/wod_tracking.py` + `student_app/views/wod_context.py`.

**Decisao:** **nao dividir em arquivos paralelos**. Adicionar bifurcacao **dentro** do `wod.html` existente:

```django
{# templates/student_app/wod.html — modificacao #}

{% if workout.is_normalized %}
    {% include "student_app/_partials/_wod_rich.html" %}
{% else %}
    {% include "student_app/_partials/_wod_raw.html" %}
{% endif %}
```

O conteudo rico atual do `wod.html` migra integralmente para `_wod_rich.html`. O `_wod_raw.html` nasce novo, simples, com texto cru em `<pre>` dentro de `student-card --quiet`.

#### Estrutura de dados — relacional, nao JSON

O render rico **continua iterando `SessionWorkoutBlock` + `SessionWorkoutMovement`** como ja faz hoje. Esses modelos relacionais sao a fonte de verdade do template.

`structured_payload` (JSON do GPT) NAO e fonte primaria de render. Ele e:
- prova de origem ("este WOD veio do SmartPlan v1.2")
- snapshot para auditoria e replay
- input para o **hydrator** que popula `SessionWorkoutBlock` + `SessionWorkoutMovement`

#### Hydrator do JSON para modelos relacionais

```python
# operations/services/wod_normalization/hydrator.py
def hydrate_session_workout_from_payload(workout, structured_payload):
    """Popula SessionWorkoutBlock e SessionWorkoutMovement a partir do JSON do GPT."""
    workout.blocks.all().delete()  # idempotente
    for block_data in structured_payload['blocks']:
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            kind=block_data['type'],
            title=block_data.get('title', ''),
            sort_order=block_data['order'],
        )
        for movement_data in block_data['movements']:
            SessionWorkoutMovement.objects.create(
                block=block,
                movement_slug=movement_data['slug'],
                movement_label=movement_data['label'],
                reps=movement_data.get('reps'),
                load_value=movement_data.get('load_kg'),
                sort_order=movement_data['order'],
            )
```

#### Tier cru — `_wod_raw.html` (NOVO)

```
┌─────────────────────────┐
│ Treino                  │
│ ─────────────           │
│ AMRAP 12: 8 BOB,        │
│ 10 hspu, 30 thruster    │
│                         │
│ [Marcar presenca]       │
└─────────────────────────┘
```

Card unico com `student-card` + variante `--quiet`. Texto cru em `<pre>` para preservar quebras de linha do coach.

#### Tier rico — `_wod_rich.html` (extraido do `wod.html` atual)

```
┌──────────────────────────────────────┐
│ AMRAP 12 minutos                     │
│ ⏱ Timer ao vivo                      │
│ ─────────────                        │
│                                      │
│ ▸ 8x Burpee Over Box                 │
│   ▶ Ver no CrossFit.com    [link]    │
│                                      │
│ ▸ 10x Handstand Push-Up              │
│   ▶ Ver no CrossFit.com    [link]    │
│   Scaling sugerido: Pike Push-Up     │
│                                      │
│ ▸ 30x Thruster   carga livre         │
│   ▶ Ver no CrossFit.com    [link]    │
│   Seu RM: 70 kg                      │
│                                      │
│ ─────────────                        │
│ 📊 Volume da semana                  │
│ Thruster: 90 reps                    │
│                                      │
│ [Marcar presenca]                    │
│ [Logar resultado]                    │
└──────────────────────────────────────┘
```

Composicao (preservando o que ja existe):
- container: `student-card` + variante `--feature` (ja em uso).
- iteracao: `student_workout_day.blocks` (ja em uso).
- novidade: link `crossfit_url` ao lado de cada movimento (Onda E.4).
- novidade: linha `Seu RM` em movimentos com slug match (Onda E.5).

### 6. Integracao com crossfit.com

Fonte canonica: `https://www.crossfit.com/crossfit-movements`.

Cada movimento canonico tem URL propria no site oficial:
- `https://www.crossfit.com/movement/thruster`
- `https://www.crossfit.com/movement/handstand-pushup`
- `https://www.crossfit.com/movement/box-jump-over`

#### Modelo MovementLibrary

```python
class MovementCategory(TextChoices):
    WEIGHTLIFTING = 'weightlifting', 'Levantamento de peso'
    GYMNASTIC     = 'gymnastic',     'Ginastico'
    MONOSTRUCTURAL = 'monostructural', 'Monoestrutural'
    OTHER         = 'other',         'Outro'

class MovementLibrary(TimeStampedModel):
    slug             = SlugField(unique=True, max_length=64)
    label_pt         = CharField(max_length=120)
    label_en         = CharField(max_length=120)
    category         = CharField(max_length=24, choices=MovementCategory.choices)
    crossfit_url     = URLField(blank=True)            # link oficial
    aliases          = JSONField(default=list)         # ['BOB', 'box jump over']
    scaling_options  = JSONField(default=list)         # [{slug, label, criterion}]
    prerequisites    = JSONField(default=list)         # outros slugs
    description_pt   = TextField(blank=True)
```

#### Sincronizacao

Inicial: lista manual curada pela OctoBOX com 30-50 movimentos do CrossFit Affiliate Programming. Cresce 2-3 por semana.

Management command para popular:
```
operations/management/commands/seed_movement_library.py
```

Le de fixture YAML em `operations/fixtures/movement_library.yaml`. Roda uma vez no deploy.

#### Regra de respeito a copyright

1. NAO reproduzir conteudo do crossfit.com.
2. APENAS linkar com `target="_blank" rel="noopener"`.
3. Descricao no OctoBOX e propria, nao copiada.
4. Video, se houver, e self-hosted ou link oficial autorizado.

### 7. Vinculo com RM do aluno

Quando `structured_payload` tem movimento que match com `StudentExerciseMax.exercise_slug`, o template renderiza:

```
▸ 30x Thruster
  Seu RM: 70 kg
```

Se o JSON do SmartPlan tiver `load_pct_rm`:
```
▸ 5x Front Squat 95%
  Seu RM: 100 kg → carga sugerida: 95 kg
```

Calculo no view:
```python
def enrich_movements_with_rm(structured_payload, student):
    rms = {rm.exercise_slug: rm.one_rep_max_kg
           for rm in student.exercise_maxes.all()}
    for block in structured_payload['blocks']:
        for movement in block['movements']:
            slug = movement['slug']
            if slug in rms:
                movement['student_rm_kg'] = float(rms[slug])
                if movement.get('load_pct_rm'):
                    movement['suggested_load_kg'] = round(
                        rms[slug] * movement['load_pct_rm'] / 100, 1
                    )
    return structured_payload
```

## Lente arquitetural

### Onde mora cada peca

```
operations/
  services/wod_normalization/             ← NOVO modulo
    __init__.py
    response_parser.py                    ← detecta formato + parseia
    hydrator.py                           ← popula SessionWorkoutBlock/Movement a partir do JSON
    prompts/
      smartplan_v1.md                     ← documentacao do prompt do GPT
  model_definitions.py                    ← + MovementLibrary, WodNormalizationRequest, SmartPlanGateEvent
  models.py                               ← + re-export de cada novo simbolo em __all__
  fixtures/movement_library.yaml          ← seed de 30-50 movimentos
  management/commands/seed_movement_library.py
  workout_editor_views.py                 ← + intent de validacao do paste (arquivo flat ja existe)
  workout_editor_dispatcher.py            ← + handler do novo intent
  workout_editor_actions.py               ← + acao de salvar com hydrator
  urls.py                                 ← + rota de validacao
  migrations/000X_smartplan.py            ← migration: 3 modelos novos + alter SessionWorkout

student_app/
  models.py                               ← + campos is_normalized, structured_payload em SessionWorkout
  views/wod_tracking.py                   ← (ja existe) sem mudanca obrigatoria
  views/wod_context.py                    ← (ja existe) garantir que retorna `is_normalized` no contexto

templates/operations/includes/
  wod_smartplan_card.html                 ← NOVO — card SmartPlan no editor
  wod_smartplan_popup.html                ← NOVO — popup de aviso (publish gate)
templates/operations/
  workout_editor_home.html                ← MODIFICAR — incluir os 2 partials acima

templates/student_app/_partials/
  _wod_rich.html                          ← NOVO — extrair conteudo rico atual do wod.html
  _wod_raw.html                           ← NOVO — texto cru em <pre>
templates/student_app/
  wod.html                                ← MODIFICAR — adicionar {% if is_normalized %} bifurcacao

static/css/
  student_app/screens/wod.css             ← (ja existe) sem mudanca
  student_app/screens/wod-rich.css        ← NOVO — composicao local do tier rico (link CF, RM line)
  operations/wod-smartplan.css            ← NOVO — card SmartPlan + popup

static/js/pages/operations/
  wod-editor-smartplan.js                 ← NOVO — clipboard handoff + popup
```

### Decisoes arquiteturais

1. **Modelos novos sem app_label historico de boxcore.** `MovementLibrary`, `WodNormalizationRequest` e `SmartPlanGateEvent` sao modelos novos nativos. Nao herdam `HISTORICAL_BOXCORE_APP_LABEL` que `ClassSession` e `Attendance` ainda carregam por compatibilidade. Eles nascem com `app_label='operations'` por default. Esta e a regra explicita do [domain-model-ownership-matrix.md](../architecture/domain-model-ownership-matrix.md) para modelos sem residuo de schema legado.
2. **Pattern `model_definitions.py -> models.py re-export`.** Os 3 modelos novos vao em `operations/model_definitions.py` e sao re-exportados em `operations/models.py` via `__all__`. Codigo da aplicacao importa apenas de `operations.models`.
3. **Extensao em modelo existente.** Os campos `is_normalized` e `structured_payload` em `SessionWorkout` ficam no `student_app/models.py` onde o modelo ja vive. Nao mover o modelo.
4. **Sem background job.** BYOLLM e sincrono — owner cola, validador parseia em <100ms, salva ou abre popup. Sem chamada externa em runtime.
5. **Listener de signal** dispara enrichment da estrutura ao salvar:
   ```python
   @receiver(post_save, sender=SessionWorkout)
   def enrich_on_normalization(sender, instance, **kwargs):
       if instance.is_normalized and instance.structured_payload:
           # resolve aliases, valida slugs contra MovementLibrary
           pass
   ```
6. **Versao do prompt como ativo.** `smartplan_v1.md` em git. Bump versao por mudanca relevante. Cada `WodNormalizationRequest` salva qual versao foi usada.
7. **Cross-domain isolation.** `student_app` consome `structured_payload` via FK soft (slug match com `MovementLibrary`), nao FK dura. Se MovementLibrary muda, render gracioso.
8. **Reuso do schema do smart-paste.** O predecessor [wod-smart-paste-corda.md](wod-smart-paste-corda.md) ja entregou `WeeklyWodPlan`, `DayPlan`, `PlanBlock`, `PlanMovement`. SmartPlan **nao cria modelos paralelos** — popula esses mesmos modelos a partir do JSON normalizado quando aplicavel. `structured_payload` em `SessionWorkout` e o snapshot canonico para o render rico; os modelos relacionais sao para queries agregadas e replicacao em massa.

### Relacao com o schema do smart-paste

O smart-paste tinha como objetivo o **parser local PT-BR** que monta semana × dia × bloco × movimento a partir de texto colado. SmartPlan substitui esse parser pelo GPT customizado que devolve formato canonico com JSON estruturado. Resultado:

1. JSON do GPT preenche `structured_payload` em `SessionWorkout` (snapshot para render rapido).
2. Quando o input cobrir uma semana inteira, o mesmo JSON pode hidratar `WeeklyWodPlan` + `DayPlan` + `PlanBlock` + `PlanMovement` para suportar replicacao.
3. WOD cru (`is_normalized=False`) nao popula essas tabelas — fica apenas em `body_text`.

### Edit flow — upgrade de raw para normalizado

Cenario real: owner publica WOD cru as 6h, percebe o problema, e quer normalizar antes da aula das 7h.

Comportamento esperado:
1. Owner abre o WOD ja publicado (mesmo `SessionWorkout`).
2. Re-abre o editor, cola output normalizado do SmartPlan, clica Publicar.
3. Sistema detecta `is_normalized` virando `False -> True`.
4. Hydrator (Onda E.3) **apaga blocos antigos** (mesmo se eram do tier raw, ainda que tipicamente raw nao popula blocos) e **cria novos** a partir do JSON.
5. `SessionWorkout.body_text` atualizado com o novo `normalized_text`.
6. Aluno que ja viu raw recebe push de cache invalidation (signal ja existente em `student_app/signals.py`).
7. `AuditEvent` registra a mudanca de tier (`wod.upgraded.raw_to_normalized`).

Caminho reverso (normalizado -> raw) **e proibido**: uma vez rich, sempre rich. Owner que quiser despublicar deve deletar e recriar.

### Concorrencia

Dois owners editando o mesmo `SessionWorkout` ao mesmo tempo: padrao do projeto e `last write wins` com `updated_at` na resposta. SmartPlan nao introduz lock novo.

Risco aceitavel para v1: muito baixo no ciclo coach -> publicar (raramente 2 pessoas no mesmo WOD ao mesmo tempo).

### Multibox e tier Pro

Projeto e single-box hoje. `Box` model existe mas o conceito de tier (`has_smartplan_pro`) nao se aplica ainda — todos os boxes recebem o mesmo SmartPlan.

A Onda E.7 (API automatica como Pro tier) **so faz sentido apos**:
1. multitenancy real estar implementada.
2. base de owners pagos atingir massa critica.

Por enquanto, BYOLLM e gratuito para todos. A telemetria de E.6 alimenta a decisao de quando ativar E.7.

### Risco arquitetural unico

**Drift do prompt do GPT**: voce edita o GPT no painel da OpenAI, mas o markdown em git pode ficar desatualizado. Sem auto-sync.

Mitigacao:
- ritual mensal: comparar GPT vivo vs `smartplan_v1.md`. Bump versao se mudou.
- pre-commit hook que pede confirmacao se editar o markdown.

## Lente CSS / front-end

### Hosts canonicos a reutilizar

| Componente | Host | Variante |
|------------|------|----------|
| Card SmartPlan no editor | `card` admin | `--accent` |
| Popup de aviso | `notice-panel` | `--warning` |
| Card raw no app aluno | `student-card` | `--quiet` |
| Card rich no app aluno | `student-card` | `--feature` |
| Bloco AMRAP/EMOM dentro do rich | composicao local em `wod-rich.css` | — |
| Movimento individual | composicao local em `wod-rich.css` | — |
| Painel de insights | `student-card` | `--quiet` |

### Alinhamento com o tema oficial

[themeOctoBox.md](../architecture/themeOctoBox.md) define "Luxo Futurista 2050" como tema canonico. SmartPlan respeita:

1. **Neon medio e localizado**: glow no card SmartPlan e no popup, nao no render do aluno (este fica acolhedor).
2. **Brilho orientando o olho**: o card "Abrir SmartPlan" no editor tem assinatura visual mais forte que o textarea — convida ao clique.
3. **Contraste premium**: popup de aviso usa `--theme-accent-danger-alpha` controlado, sem agressao.
4. **Atmosfera de cockpit**: tier rico do aluno parece painel de avioacao (timer ao vivo, metricas), nao planilha.

### O que NAO criar

1. NAO criar `glass-panel` novo, `wod-card` novo, ou qualquer host paralelo.
2. NAO redefinir tokens de cor, sombra ou borda em `wod-rich.css` — usar apenas `var(--theme-*)`.
3. NAO usar `!important` no CSS local.
4. NAO inline style em template.
5. NAO usar familias legado proibidas (`finance-glass-panel`, `note-panel*`, `elite-glass-card`) per [css-guide.md](../experience/css-guide.md).

### O que `wod-rich.css` faz

Apenas composicao local:
- grid de movimentos
- linha de scaling
- linha de RM/carga sugerida
- separadores entre blocos
- icones e setas

Codigo esperado: <200 linhas.

### Versionamento de assets

Seguir o padrao do projeto: registrar arquivo em `build_catalog_assets` ou equivalente do student_app, usar `?v={{ static_asset_version }}` no link.

### Mobile-first

App do aluno e mobile-first. Garantir:
- card rich nao quebra em viewport <360px.
- timer AMRAP fica sticky no topo durante a aula.
- movimentos colapsam para acordeon em viewport pequeno (opcional na onda inicial).

## Lente UX / conversao

### O popup e o cartao mais importante do produto

E o ponto onde a OctoBOX toma postura clara: voce **pode** publicar cru, mas voce **vai sentir** a perda. Esse popup e marketing interno embutido na ferramenta.

### Aplicacao de loss aversion

Pesquisa de psicologia comportamental: pessoas reagem 2x mais forte a perda do que a ganho.

Texto errado:
> "Use SmartPlan para um WOD melhor."

Texto certo:
> "Sem SmartPlan, voce **perde** videos, metricas e PR detection."

A lista do popup deve **enumerar perdas concretas**, nao prometer ganhos abstratos.

### Hierarquia de botoes no popup

1. Botao primario (azul/verde): **"Voltar e formatar com SmartPlan"** — caminho desejado.
2. Botao secundario (cinza ou red-tint): **"Publicar mesmo assim"** — escape valido mas desincentivado.

NUNCA inverter. NUNCA igualar peso visual.

### Telemetria obrigatoria

Cada decisao no popup e dado de produto:

```python
class SmartPlanGateEvent(TimeStampedModel):
    workout      = FK(SessionWorkout)
    actor        = FK(User)
    decision     = CharField(choices=[
        ('formatted',   'Formatou via SmartPlan'),
        ('back',        'Voltou para formatar'),
        ('raw_anyway',  'Publicou cru mesmo assim'),
    ])
    box_root_slug = CharField(max_length=64)
```

Metricas alvo no primeiro mes:
- % de WODs publicados como `formatted` por box.
- % de owners que clicam "Voltar e formatar" depois de ver o popup pela primeira vez.
- tempo medio entre abrir o GPT e colar a resposta.

Boxes com >70% de `formatted` no mes 2 sao **case studies**. Boxes com <30% sao **alvo de outreach** ("podemos ajudar a configurar?").

### Funil de conversao

```
[Owner abre editor]              100%
[Clica "Abrir SmartPlan"]         70%  ← baseline alvo
[Cola resposta no editor]         60%
[Formato valido na primeira]      50%
[Publicado como rico]             50%
```

Cada degrau e oportunidade de melhoria. Se "Cola resposta" cai muito (60% → 30%), o caminho do GPT esta confuso. Se "Formato valido" cai (60% → 20%), o prompt do GPT esta fraco.

### Premium framing futuro

Quando a Onda E.6 (API automatica) chegar, o framing ja esta pronto:

> "Cansou de copiar e colar? **OctoBOX Pro** normaliza automaticamente. R$ 39/mes."

A friccao do BYOLLM e a **demonstracao de valor** que justifica o upgrade. Sem BYOLLM primeiro, ninguem paga pelo Pro.

## Ondas de implementacao

### Onda E.1 — Validador + popup + tier flag (1 dia)

**Objetivo:** schema + validacao + UX de gating, sem render rico ainda.

**Arquivos:**
- `operations/services/wod_normalization/__init__.py` (NOVO)
- `operations/services/wod_normalization/response_parser.py` (NOVO)
- `operations/services/wod_normalization/prompts/smartplan_v1.md` (NOVO — doc do GPT, fonte de verdade do prompt)
- `operations/workout_editor_views.py` (modificar para receber paste e chamar parser)
- `operations/workout_editor_dispatcher.py` (modificar — adicionar intent `validate_smartplan_paste`)
- `operations/workout_editor_actions.py` (modificar — bifurcar `publish` baseado no resultado da validacao)
- `templates/operations/includes/wod_smartplan_card.html` (NOVO)
- `templates/operations/includes/wod_smartplan_popup.html` (NOVO)
- `templates/operations/workout_editor_home.html` (modificar — incluir os 2 partials)
- `static/js/pages/operations/wod-editor-smartplan.js` (NOVO)
- `static/css/operations/wod-smartplan.css` (NOVO)
- `student_app/models.py` (modificar — adicionar 2 campos em `SessionWorkout`):
  - `is_normalized = BooleanField(default=False)`
  - `structured_payload = JSONField(default=dict, blank=True)`
- `student_app/migrations/00XX_sessionworkout_smartplan_fields.py` (NOVO)

**Criterio de done:**
- coach cola texto cru → popup aparece com 6 perdas listadas.
- "Voltar e formatar" volta ao editor preservando texto.
- "Publicar mesmo assim" salva com `is_normalized=False`, `body_text` preenchido, `structured_payload={}`.
- coach cola texto formatado valido → salva com `is_normalized=True`, `structured_payload` preenchido.
- testes cobrem 5 casos: formato valido, sem marcadores, JSON invalido, JSON valido mas sem campo `blocks`, JSON com `blocks=[]`.

### Onda E.2 — GPT customizado publicado (0.5 dia)

**Objetivo:** publicar o GPT na conta da OctoBOX e fixar URL no settings.

**Tarefas:**
1. Criar GPT no editor `https://chatgpt.com/gpts/editor/...`.
2. Colar instrucoes de `smartplan_v1.md` no campo Instructions.
3. Adicionar 5 exemplos few-shot no campo Conversation Starters.
4. Publicar como "Anyone with link".
5. Fixar URL em `config/settings/base.py`:
   ```python
   SMARTPLAN_GPT_URL = 'https://chatgpt.com/g/g-XXXXX-octobox-smartplan'
   ```
6. Renderizar URL no template do editor de WOD.

**Criterio de done:**
- URL acessivel sem login da OctoBOX.
- 3 testes manuais com WODs reais retornam formato canonico.

### Onda E.3 — Render rico baseline + hydrator (1.5 dias)

**Objetivo:** WOD normalizado popula `SessionWorkoutBlock`/`SessionWorkoutMovement` a partir do JSON; app do aluno bifurca render no `wod.html` existente.

**Arquivos:**
- `operations/services/wod_normalization/hydrator.py` (NOVO — popula modelos relacionais)
- `operations/workout_editor_actions.py` (modificar — chama hydrator quando `is_normalized=True`)
- `student_app/views/wod_context.py` (modificar — expor `is_normalized` no contexto da view)
- `templates/student_app/wod.html` (modificar — adicionar `{% if workout.is_normalized %}` bifurcacao)
- `templates/student_app/_partials/_wod_rich.html` (NOVO — extrair conteudo rico ja existente do `wod.html`)
- `templates/student_app/_partials/_wod_raw.html` (NOVO — texto cru em `<pre>` dentro de `student-card --quiet`)
- `static/css/student_app/screens/wod-rich.css` (NOVO — composicao local do tier rico)

**Criterio de done:**
- ao salvar WOD com `is_normalized=True`, o hydrator preenche `SessionWorkoutBlock` + `SessionWorkoutMovement` a partir de `structured_payload`.
- WOD com `is_normalized=True` renderiza `_wod_rich.html` que itera os blocos relacionais (igual ao comportamento atual).
- WOD com `is_normalized=False` renderiza `_wod_raw.html` com texto cru em `<pre>`.
- migracao raw->rich e idempotente: re-publicar com SmartPlan apaga blocos antigos e recria.
- testes cobrem: hydrator popula corretamente, hydrator e idempotente, view bifurca correto.

### Onda E.4 — MovementLibrary + crossfit.com sync (1.5 dias)

**Objetivo:** linkar cada movimento ao site oficial do CrossFit.

**Arquivos:**
- `operations/model_definitions.py` (modificar — adicionar `MovementLibrary` com `app_label='operations'`)
- `operations/models.py` (modificar — re-exportar `MovementLibrary` em `__all__`)
- `operations/migrations/00XX_movementlibrary.py` (NOVO)
- `operations/fixtures/movement_library.yaml` (NOVO — 30-50 movimentos canonicos com URL)
- `operations/management/commands/seed_movement_library.py` (NOVO)
- `templates/student_app/_partials/_wod_rich.html` (modificar — adicionar link "Ver no CrossFit.com" ao lado de cada movimento que tem `crossfit_url`)

**Validacao previa de URL pattern:**

Antes de seed, validar que o padrao de URL do CrossFit oficial e estavel (ex: `https://www.crossfit.com/movement/<slug>`). Se nao for, fixar URL completa no YAML por movimento, sem montar dinamicamente.

**Movimentos prioritarios na seed inicial:**

```yaml
- slug: thruster
  label_pt: Thruster
  label_en: Thruster
  category: weightlifting
  crossfit_url: https://www.crossfit.com/movement/thruster
  aliases: [thruster]
- slug: burpee_over_box
  label_pt: Burpee Sobre Caixa
  label_en: Burpee Over Box
  category: gymnastic
  crossfit_url: https://www.crossfit.com/movement/burpee-box-jump-over
  aliases: [BOB, burpee box jump over]
# ... 30-50 movimentos
```

**Criterio de done:**
- seed roda em <2s.
- cada movimento no rich render tem link para crossfit.com com `target="_blank" rel="noopener"`.
- movimento sem match no library renderiza sem link, sem quebrar.

### Onda E.5 — Vinculo RM + scaling sugerido (1 dia)

**Objetivo:** mostrar RM do aluno e sugestao de carga em movimentos com `load_pct_rm`.

**Arquivos:**
- `student_app/views/wod_context.py` (modificar — adicionar `enrich_movements_with_rm` no contexto)
- `templates/student_app/_partials/_wod_rich.html` (modificar — exibir linha "Seu RM: X kg → carga sugerida: Y kg")
- `static/css/student_app/screens/wod-rich.css` (modificar — estilos da linha de RM)

**Criterio de done:**
- movimento com slug que match `StudentExerciseMax` mostra RM do aluno.
- movimento com `load_pct_rm` no JSON mostra carga sugerida calculada.
- movimento sem match nao mostra linha de RM (graceful).
- aluno sem RM cadastrado nao quebra render.

### Onda E.6 — Telemetria de gate + auditoria (0.5 dia)

**Objetivo:** instrumentar o popup com `SmartPlanGateEvent` para medir conversao e gravar `AuditEvent` para rastreabilidade.

**Arquivos:**
- `operations/model_definitions.py` (modificar — adicionar `SmartPlanGateEvent` com `app_label='operations'`)
- `operations/models.py` (modificar — re-exportar `SmartPlanGateEvent` em `__all__`)
- `operations/migrations/00XX_smartplan_gate_event.py` (NOVO)
- `operations/workout_editor_actions.py` (modificar — emitir `SmartPlanGateEvent` em cada decisao + emitir `AuditEvent` via `auditing.services` quando WOD e publicado)
- dashboard de owner com 3 metricas: `% formatted`, `% raw_anyway`, `tempo medio GPT`

**Auditoria obrigatoria:**

Toda publicacao de WOD (raw ou normalizado) emite `AuditEvent` seguindo o padrao do projeto em `auditing/services.py`. Campos:
- `actor` = user que clicou Publicar
- `action` = `wod.published.normalized` ou `wod.published.raw`
- `target` = `SessionWorkout.id`
- `metadata` = `{'prompt_version': '...', 'gate_decision': '...'}`

**Criterio de done:**
- 3 decisoes geram 3 eventos distintos.
- query de % por box roda em <100ms para 1000 eventos.
- dashboard owner mostra graficos da semana atual.

### Onda E.7 (futuro) — API automatica como Pro tier

Quando metricas mostrarem que >30% dos owners normalizam semanalmente, abrir feature paga: OctoBOX faz a chamada de API direto, owner nao precisa abrir GPT.

Reusa toda a infra ja construida. Adiciona:
- `submit_background_job(_call_smartplan_api, request_id)`.
- billing flag em `Box.has_smartplan_pro`.

## Ordem de execucao

```
Sprint atual:
  E.1   Validador + popup + flag       1 dia
  E.2   Publicar GPT + fixar URL       0.5 dia
  E.3   Render rico baseline           1.5 dias
                                       ------
                                       3 dias

Sprint seguinte:
  E.4   MovementLibrary + crossfit.com 1.5 dias
  E.5   Vinculo RM + scaling           1 dia
  E.6   Telemetria do gate             0.5 dia
                                       ------
                                       3 dias

Total v1 SmartPlan:                    6 dias-PR

Futuro condicional:
  E.7   API automatica (Pro tier)      ~3 dias
```

## Posicao no plano geral de ondas

```
Esta semana:     Onda A          ← notificacoes
Proximo ciclo:   Onda E.1-E.3    ← SmartPlan baseline (3 dias)
Apos:            Onda E.4-E.6    ← SmartPlan completo (3 dias)
Depois:          Onda B          ← cron
Sprint:          Onda C          ← PR workflow
Buffer:          Onda D          ← challenges
Futuro:          Onda F          ← ML insights sobre structured_payload
Premium:         Onda E.7        ← API automatica
```

## Sinais de saude do SmartPlan

1. >50% dos WODs do mes 2 sao publicados como `formatted`.
2. Tempo medio entre "Abrir SmartPlan" e "Cola resposta" e <90s.
3. Taxa de erro de parsing (formato invalido apos passar pelo GPT) e <5%.
4. Boxes que adotaram SmartPlan tem maior abertura diaria do app do aluno do que boxes em texto cru.

## Sinais de que o SmartPlan saiu do trilho

1. Owner aprende a colar texto cru rapido e ignora o popup sistematicamente.
2. Coach reclama do GPT (formato chato, demora, output ruim).
3. Renders rich quebram em movimentos comuns por falta de seed na MovementLibrary.
4. Telemetria mostra <20% de adocao no mes 1 sem outreach explicito.

## Decisoes que nao sao deste documento

1. Nome comercial final do feature (SmartPlan vs WOD Pro vs WOD Detalhado) — decidir com marketing.
2. Pricing do tier Pro (Onda E.7) — decidir com base em telemetria do v1.
3. Lista exata dos 30-50 movimentos da seed — escopo do trabalho de conteudo, nao da engenharia.
4. Texto exato do popup — copy a iterar com base em A/B test apos v1.
