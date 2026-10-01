"""
ARQUIVO: filtros de template do corredor publico de treinos (/renan/).

POR QUE ELE EXISTE:
- o payload de PublicWorkoutProgram (public_workouts/schema.py) carrega so
  `movement_slug`, nunca um label pronto pra exibir — a mesma logica de
  "melhor palpite legivel" ja usada em services.py::_ensure_movements_exist
  pro catalogo, repetida aqui pro template nao depender de outra consulta
  ao banco so pra mostrar um nome.
- load_chart_points (Onda B4, fatia adiantada) e' o equivalente Python de
  static/js/public_workouts/assessments.js::buildWeightChart — devolve
  dado puro (pontos normalizados), nunca HTML pronto, pra manter o
  autoescape do Django e deixar o teste assertar em numeros, nao em
  substring de SVG. O <svg>/<polyline> fica no template que chama o filtro.
  Tambem marca `is_program_change` por ponto (Pronto-quando #2 da secao
  A3/B4 do CORDA) — onde `program_id` muda entre dois registros
  consecutivos, o template desenha o marcador de troca de versao.
- dict_get existe porque o Django template nao tem subscript por variavel
  (`dicionario[chave]` so aceita chave literal) — `one_rep_max_by_movement`
  e `trends_by_movement` (Onda A3, ja calculados em services.py) sao dicts
  chaveados por `movement_slug`, e o template precisa deles dentro do
  `{% regroup %}` por movimento.
- workout_greeting/initial (fundacao visual do topbar, pedido do Renan)
  sao um duplicado deliberado de student_app/templatetags/student_shell.py
  ({% load student_shell %} do template deste produto violaria D.00/D.3 —
  ver docstring de workout.html). A logica e trivial (nem 10 linhas) e nao
  depende de nenhum modelo — duplicar aqui e mais barato que arriscar
  acoplamento entre produtos so pra nao repetir um if/elif de horario.
"""

from __future__ import annotations

import re
from datetime import date as _date, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from django import template
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.html import escape
from django.utils.safestring import mark_safe

from public_workouts.dashboard import (
    build_program_summary, build_week_overview, build_workout_day_selection, day_keyword, day_short_label,
)
from public_workouts.load_suggestion import suggest_movement_load
from public_workouts.progress_eligibility import eligible_for_personal_record, eligible_for_progress_curve
from public_workouts.periodization import (
    build_chart_points_from_weeks,
    current_phase_profile,
    current_week_number,
    suggest_progressive_load_kg,
)
from public_workouts.models import PublicWorkoutMovement, PublicWorkoutMovementEquipment
from public_workouts.substitutions import suggest_substitutes
from public_workouts.warmup_ramp import extract_leading_set_count, stage_ramp_kg

register = template.Library()


@register.simple_tag
def program_summary(payload: dict) -> dict:
    """Wrapper de template pra dashboard.build_program_summary — o template
    so tem `program` (o payload) no contexto, nao precisa de var nova."""
    return build_program_summary(payload)


@register.simple_tag
def week_streak_label(week_days) -> str:
    """'2 de 4 dias com treino' — mesma logica de complete_count do app do
    aluno (student_shell.py), so que o denominador aqui e' os dias
    PRESCRITOS (has_program), nao os 7 dias corridos — programa do
    corredor tem dia de descanso fixo por semana, "0 de 7" seria enganoso."""
    prescribed = [day for day in week_days if day.has_program]
    if not prescribed:
        return ''
    completed = sum(1 for day in prescribed if day.is_complete)
    return f'{completed} de {len(prescribed)} dia{"s" if len(prescribed) != 1 else ""} com treino'


@register.filter
def day_short(day_id: str) -> str:
    """Wrapper de template pra dashboard.day_short_label — dia curto (Seg/
    Ter/...) reusado no seletor de dia do Treino (item pedido pelo Renan:
    mesmo formato "dia + palavra-chave" do "Sua semana" do Início)."""
    return day_short_label(day_id)


@register.simple_tag
def day_workout_keyword(day) -> str:
    """Wrapper de template pra dashboard.day_keyword — recebe o `day` do
    payload inteiro (nao so' os campos soltos) pra assinatura ficar simples
    no template: `{% day_workout_keyword day %}`."""
    return day_keyword(day_id=day.get('day_id', ''), label=day.get('label', ''))


@register.simple_tag
def week_overview(payload: dict, load_history=None) -> list:
    """Wrapper de template pra dashboard.build_week_overview — converte as
    datas ISO string de `load_history` (mesmo shape de services.list_load_history)
    pra `date` antes de chamar a funcao pura."""
    completed_dates = set()
    for entry in load_history or ():
        performed_on = entry.get('performed_on') if hasattr(entry, 'get') else None
        if not performed_on:
            continue
        completed_dates.add(_date.fromisoformat(performed_on) if isinstance(performed_on, str) else performed_on)
    return build_week_overview(payload=payload, completed_dates=completed_dates, today=timezone.localdate())


@register.simple_tag
def workout_day_selection(payload: dict) -> dict:
    """Dia inicial do treino pelo calendário semanal; descanso aponta para
    a próxima sessão para pré-visualização, com estado explícito no HTML."""
    return build_workout_day_selection(payload=payload, today=timezone.localdate())


@register.simple_tag
def workout_greeting(name: str = '') -> str:
    """Saudação por hora local + primeiro nome ('Boa tarde, Juliana').

    Mesmo relogio/faixas de horario de student_shell.student_greeting —
    duplicado de proposito (ver docstring do modulo), nao importado.
    """
    hour = timezone.localtime().hour
    if hour < 12:
        greeting = 'Bom dia'
    elif hour < 18:
        greeting = 'Boa tarde'
    else:
        greeting = 'Boa noite'

    first_name = (name or '').strip().split(' ')[0]
    return f'{greeting}, {first_name}' if first_name else greeting


@register.filter
def initial(name: str) -> str:
    """'Juliana' -> 'J' — fallback de avatar antes de existir foto."""
    stripped = (name or '').strip()
    return stripped[0].upper() if stripped else '?'


@register.filter
def humanize_movement_slug(movement_slug: str) -> str:
    """'agachamento-livre' -> 'Agachamento livre'. Mesmo palpite de
    services.py::_ensure_movements_exist — nao consulta PublicWorkoutMovement
    (o template pode receber um payload que ainda nem foi publicado)."""
    if not movement_slug:
        return ''
    return movement_slug.replace('-', ' ').capitalize()


@register.filter
def movement_name(movement: dict, movement_labels: dict | None = None) -> str:
    """Nome pra exibir na tela — uniao das DUAS fontes PT-BR que surgiram em
    paralelo (duas sessoes, mesmo problema): `movement.name` (portugues,
    escrito pelo treinador nesta VERSAO do payload — aditivo, ver
    schema.py) tem prioridade quando presente; senao cai pro catalogo
    retroativo (`movement_labels`, services.build_movement_label_lookup,
    Onda A0 — cobre os 10 programas legados que ainda nao tem `name` no
    payload); senao humaniza `movement_slug`. Delega a resolucao dos dois
    ultimos casos pra resolve_movement_display_name (mesma logica, testada
    a parte) em vez de duplicar."""
    movement = movement or {}
    name = movement.get('name')
    if name:
        return name
    return resolve_movement_display_name(movement.get('movement_slug', ''), movement_labels)


@register.filter
def sibling_variations(movement_slug: str) -> list[dict]:
    """"Variação irmã" (Onda A3/B4, item 3 do "Pronto quando" do CORDA) —
    outros movimentos ATIVOS do MESMO `movement_pattern` (catálogo,
    `PublicWorkoutMovement`), exibidos na aba Cargas como REFERÊNCIA ao
    lado do gráfico do movimento — nunca entram no cálculo de 1RM/
    tendência daquele `movement_slug` (que fica estritamente isolado por
    slug, ver docstring de one_rep_max.py: "NUNCA compara 1RM entre
    movement_slug diferentes"). Reusa `suggest_substitutes` (Onda A3,
    já existia) tal e qual — nenhuma lógica nova, só a exibição que
    faltava. Lista vazia (nunca quebra o template) quando o movimento
    não está classificado ou não tem irmã ativa no catálogo."""
    return suggest_substitutes(movement_slug=movement_slug, limit=3)


@register.filter
def movement_shows_plate_calculator(movement_slug: str) -> bool:
    """Plano curva-carga-completa-reps-rir-recorde, Fase 3 (§5.1): a
    calculadora de anilhas só aparece quando os DOIS metadados curados
    batem — `equipment_type='barbell'` E `logged_weight_includes_bar`.
    equipment_type sozinho não prova a convenção de registro (um
    treinador pode pedir só o peso das anilhas, sem a barra); os dois
    juntos exigem curadoria humana explícita, nunca inferência automática
    de `movement_pattern`/nome (mesmo cuidado de `suggest_substitutes`).
    `False` (nunca quebra o template) quando o slug não está no catálogo."""
    movement = PublicWorkoutMovement.objects.filter(slug=movement_slug).first()
    if movement is None:
        return False
    return movement.equipment_type == PublicWorkoutMovementEquipment.BARBELL and movement.logged_weight_includes_bar


_GLOSSARY_TERMS = {
    'rir': ('RIR (Reps in Reserve)', 'Repetições que ainda sobrariam na reserva se a série continuasse até a falha. Ex.: RIR 2 = parou a 2 repetições da falha.'),
    'amrap': ('AMRAP (As Many Reps As Possible)', 'Fazer o máximo de repetições possível na série, dentro da técnica segura.'),
    'feeder': ('Série Feeder', 'Série leve de ativação antes da série principal (Top) — prepara a articulação e o padrão de movimento sem gerar fadiga.'),
    'top': ('Série Top (Top Set)', 'A série mais pesada do exercício no dia — o estímulo-alvo do treino, feita depois do aquecimento/feeder.'),
    'prep': ('Série Prep (preparatória)', 'Série de aquecimento específico com carga leve/moderada, antes das séries de trabalho.'),
    'max': ('Max Set', 'Série final no mesmo peso do Top Set, feita até o máximo de repetições possíveis (AMRAP) — mede quantas reps sobram naquela carga, não é uma carga nova.'),
}

_GLOSSARY_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(term) for term in _GLOSSARY_TERMS) + r')\b',
    re.IGNORECASE,
)


def _format_ramp_kg_sentence(weights: list[float]) -> str:
    formatted = ' → '.join(number_format(weight, decimal_pos=1) + ' kg' for weight in weights)
    return f' Peso sugerido: {formatted}.'


@register.filter
def glossary_highlight(text: str, ramp=None):
    """Marca termos de jargao de treino (RIR, AMRAP, Feeder, Top, Prep) dentro
    de reps_spec/rir_spec (texto livre do treinador, schema.py) com uma
    'bolinha' clicavel que revela a definicao — pedido do Renan pra quem
    nao conhece o dicionario de treino.

    So estes 6 termos: sao os que realmente aparecem nos 10 programas reais
    publicados (conferido via payload, nao adivinhado) — nao generaliza pra
    qualquer palavra tecnica, que arriscaria falso-positivo (ex. 'top' dentro
    de 'topo' e' evitado com \\b, mas uma lista maior sem curadoria arriscaria
    marcar termo errado como se fosse dicionario de treino).

    `ramp`: tupla opcional `(stage_key, pesos_kg)` (`warmup_ramp.stage_ramp_kg`,
    ver `reps_phases` abaixo) — quando o termo casado (case-insensitive) for
    EXATAMENTE esse `stage_key` (prep/feeder/top/max), a dica ganha uma
    linha extra com o(s) peso(s) sugerido(s) pra essa fase NESTE exercicio,
    nesta semana. Nunca aparece pros outros termos (RIR/AMRAP sem stage
    correspondente aqui nao tem peso pra sugerir).

    Retorna SafeString: escapa o texto ao redor, so o termo casado vira HTML.
    """
    if not text:
        return ''

    ramp_stage, ramp_weights = ramp if ramp else (None, None)

    pieces = []
    last_end = 0
    for match in _GLOSSARY_PATTERN.finditer(text):
        pieces.append(escape(text[last_end:match.start()]))
        term = match.group(0)
        term_key = term.lower()
        label, description = _GLOSSARY_TERMS[term_key]
        if ramp_weights and term_key == ramp_stage:
            description = description + _format_ramp_kg_sentence(ramp_weights)
        pieces.append(
            '<span class="workout-glossary-term" data-workout-glossary tabindex="0" role="button" aria-expanded="false" aria-label="O que é {label}?">'
            '{term}<sup class="workout-glossary-dot" aria-hidden="true">ⓘ</sup>'
            '<span class="workout-glossary-tip" role="tooltip"><strong>{label}</strong>{description}</span>'
            '</span>'.format(
                label=escape(label),
                term=escape(term),
                description=escape(description),
            )
        )
        last_end = match.end()
    pieces.append(escape(text[last_end:]))
    return mark_safe(''.join(pieces))


_PHASE_DETECTORS = (
    ('prep', re.compile(r'\bprep', re.IGNORECASE)),
    ('feeder', re.compile(r'\bfeeder', re.IGNORECASE)),
    ('top', re.compile(r'\btop\b', re.IGNORECASE)),
    ('max', re.compile(r'\bamrap\b|\bmax\b', re.IGNORECASE)),
)


def _detect_phase(segment: str) -> str:
    for phase, pattern in _PHASE_DETECTORS:
        if pattern.search(segment):
            return phase
    return 'plain'


@register.filter
def reps_phases(reps_spec: str, top_weight_kg=None):
    """Quebra `reps_spec` em fases (Prep/Feeder/Top/AMRAP) quando o texto do
    treinador junta varias com ' → ' (ex.: '2-3× Prep → 1× Feeder → 3× Top
    (6-8)', formato de `gym-reps` nos 8 dos 10 templates legados que tem
    esse padrao — ver parser.py). Devolve lista de dicts {text, phase} pro
    template desenhar um "chip" colorido por fase (pedido do Renan: "voltar
    o padrao de feeder/topset/amrap"), ou lista VAZIA quando so' ha 1 fase —
    nesse caso o template mantem a linha simples de sempre (nao vale a pena
    um chip grande pra 'reps_spec': '3x12', a maioria dos movimentos sem
    quebra de fase).

    `top_weight_kg` (opcional, `{{ movement.reps_spec|reps_phases:load.value_kg }}`
    no template, `load` já vindo de `movement_load_display`): quando
    presente, cada fase Prep/Feeder/Top/Max ganha um ramp de carga
    (`warmup_ramp.stage_ramp_kg`) embutido na PRÓPRIA dica de glossário
    daquele chip — pedido do Renan: "ao registrar a kilagem aparecer a
    kilagem apropriada no balão". Sincronizado com a periodização de
    graça: `top_weight_kg` já veio da cascata de `movement_load_display`
    (fase progressiva quando existe), então o ramp muda junto quando o Top
    muda de semana pra semana — nunca um segundo cálculo desalinhado.

    Cada `text` ja passa por glossary_highlight (SafeString) — o template
    nao precisa aplicar o filtro de novo.
    """
    if not reps_spec:
        return []
    segments = [segment.strip() for segment in reps_spec.split('→') if segment.strip()]
    if len(segments) < 2:
        return []

    phases = []
    for segment in segments:
        stage = _detect_phase(segment)
        ramp = None
        if top_weight_kg:
            set_count = extract_leading_set_count(segment)
            weights = stage_ramp_kg(stage=stage, set_count=set_count, top_weight_kg=top_weight_kg)
            if weights:
                ramp = (stage, weights)
        phases.append({'text': glossary_highlight(segment, ramp), 'phase': stage})
    return phases


@register.filter
def resolve_movement_display_name(movement_slug: str, movement_labels: dict | None) -> str:
    """Onda B3 — nome de exercicio pra exibir: PT-BR de verdade quando
    `movement_labels` (services.build_movement_label_lookup, uma query em
    lote contra PublicWorkoutMovement) tem entrada pro slug, senao o
    mesmo palpite mecanico de humanize_movement_slug. Filtro proprio (nao
    `default` encadeado com humanize_movement_slug) de proposito: um rotulo
    de verdade tipo "Wall Ball" ou "GHD Sit-up" passado por
    humanize_movement_slug sairia errado (`.capitalize()` derruba as
    maiusculas internas)."""
    if movement_labels:
        label = movement_labels.get(movement_slug)
        if label:
            return label
    return humanize_movement_slug(movement_slug)


@register.filter
def dict_get(dictionary: dict | None, key: str):
    """Lookup generico por chave variavel — Django template so faz
    `dicionario.chave` (subscript literal). Devolve None se o dict for
    None/vazio ou a chave nao existir (template so precisa de `{% if %}`,
    nao de tratamento de excecao)."""
    if not dictionary:
        return None
    return dictionary.get(key)


_CHART_WIDTH = 600
_CHART_HEIGHT = 100
_CHART_PAD = 10


def _format_short_date(iso_date: str | _date) -> str:
    """'2026-01-05' -> '05/01'. Rotulo compacto de eixo do mini-grafico —
    nao e' formatacao de data generica do app (list_program_versions, por
    exemplo, deixa a data ISO crua de proposito, pra outro uso)."""
    iso_date = iso_date.isoformat() if isinstance(iso_date, _date) else iso_date
    parts = iso_date.split('-')
    if len(parts) != 3:
        return iso_date
    _year, month, day = parts
    return f'{day}/{month}'


def _format_long_date(value) -> str:
    """Format an ISO/date value for a visible record label."""
    if isinstance(value, _date):
        return value.strftime('%d/%m/%Y')
    try:
        return _date.fromisoformat(str(value)).strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return str(value or '')


def _trend(delta: float) -> str:
    if delta > 0:
        return 'up'
    if delta < 0:
        return 'down'
    return 'flat'


@register.filter
def load_chart_points(entries: list[dict]) -> dict:
    """Converte uma serie de registros de carga (mesmo shape de
    services.list_load_history, ja em ordem cronologica) nos pontos
    normalizados de um mini-grafico SVG.

    `has_data=False` (com listas vazias) quando ha menos de 2 pontos com
    `weight_kg` preenchido — mesma supressao de buildWeightChart (um unico
    ponto nao mostra tendencia nenhuma; movimentos so de peso corporal, sem
    weight_kg, tambem caem aqui).

    Alem dos pontos da linha, devolve `area_points_attr` (a mesma linha
    fechada na base do grafico — `baseline_y` — pra preencher um degrade
    embaixo da curva) e `latest_weight_kg`/`delta_weight_kg`/`trend`
    (primeiro vs. ultimo ponto), pra exibir o valor atual e a tendencia sem
    o template precisar indexar a lista (Django template nao tem `[-1]`)."""
    baseline_y = _CHART_HEIGHT - _CHART_PAD
    # Plano curva-grafico-hierarquia-e-set-role.md, §2.1/§2.2: a linha so'
    # pode conectar series COMPARAVEIS -- so' top_set (eligible_for_
    # progress_curve) entra na curva principal. O template de produção usa
    # o snapshot (progress_chart_for_movement) para mostrar legado como
    # pontos neutros e sem conexão -- este filtro/função permanece so'
    # pro caminho de teste direto (test_workout_template.py), nao esta'
    # mais no caminho real de renderização.
    weighted = [
        entry for entry in entries
        if entry.get('weight_kg') is not None and eligible_for_progress_curve(entry)
    ]
    if len(weighted) < 2:
        return {
            'has_data': False,
            'viewbox': f'0 0 {_CHART_WIDTH} {_CHART_HEIGHT + 20}',
            'label_y': _CHART_HEIGHT + 15,
            'baseline_y': baseline_y,
            'points_attr': '',
            'area_points_attr': '',
            'points': [],
            'latest_weight_kg': None,
            'delta_weight_kg': None,
            'trend': 'flat',
        }

    weights = [entry['weight_kg'] for entry in weighted]
    min_weight, max_weight = min(weights), max(weights)
    span = (max_weight - min_weight) or 1
    step_x = (_CHART_WIDTH - _CHART_PAD * 2) / (len(weighted) - 1)

    points = []
    previous_program_id = None
    for index, entry in enumerate(weighted):
        x = round(_CHART_PAD + index * step_x, 2)
        y = round(
            _CHART_HEIGHT - _CHART_PAD - ((entry['weight_kg'] - min_weight) / span) * (_CHART_HEIGHT - _CHART_PAD * 2),
            2,
        )
        program_id = entry.get('program_id') or ''
        # So marca troca quando os DOIS lados sao um programa de verdade —
        # o primeiro ponto da serie nunca marca (nao ha "antes" pra
        # contrastar) e `program_id=''` (carga sem programa associado)
        # nunca conta como troca, so ruido.
        is_program_change = bool(
            index > 0 and program_id and previous_program_id and program_id != previous_program_id
        )
        points.append({
            'x': x,
            'y': y,
            'weight_kg': entry['weight_kg'],
            'performed_on': entry['performed_on'],
            'label': _format_short_date(entry['performed_on']),
            'program_id': program_id,
            'week_in_program': entry.get('week_in_program'),
            'is_program_change': is_program_change,
        })
        previous_program_id = program_id or previous_program_id

    points_attr = ' '.join(f"{point['x']},{point['y']}" for point in points)
    area_points_attr = f"{points_attr} {points[-1]['x']},{baseline_y} {points[0]['x']},{baseline_y}"
    delta = round(points[-1]['weight_kg'] - points[0]['weight_kg'], 2)

    return {
        'has_data': True,
        'viewbox': f'0 0 {_CHART_WIDTH} {_CHART_HEIGHT + 20}',
        'label_y': _CHART_HEIGHT + 15,
        'baseline_y': baseline_y,
        'points_attr': points_attr,
        'area_points_attr': area_points_attr,
        'points': points,
        'latest_weight_kg': points[-1]['weight_kg'],
        'delta_weight_kg': delta,
        'trend': _trend(delta),
    }

@register.simple_tag
def progress_chart_for_movement(movement_slug: str, progress_snapshots: dict) -> dict:
    """Render data prepared by progress_snapshot, never rescan raw history.

    The horizontal axis uses the fixed 90-day window and the vertical scale
    uses the snapshot's rounded plate increments. Legacy records stay as
    isolated neutral points and never join the top-set polyline.
    """
    snapshot = (progress_snapshots or {}).get(movement_slug)
    baseline_y = _CHART_HEIGHT - _CHART_PAD
    plot_height = _CHART_HEIGHT - _CHART_PAD * 2
    # Reserve a quiet rail for absolute-scale labels so they never sit on
    # top of the first data point.
    x_left, x_right = 46, _CHART_WIDTH - _CHART_PAD
    as_of = snapshot.as_of if snapshot and getattr(snapshot, 'as_of', None) else timezone.localdate()
    window_start = as_of - timedelta(days=90)

    def point_date(point):
        value = point.performed_on
        return value if isinstance(value, _date) else _date.fromisoformat(str(value))

    curve_points = list(snapshot.curve_points) if snapshot else []
    legacy_points = list(snapshot.legacy_points) if snapshot else []
    weighted = [point for point in curve_points if point.weight_kg is not None]
    scale = snapshot.y_scale if snapshot else None
    if scale is None:
        legacy_weights = [point.weight_kg for point in legacy_points if point.weight_kg is not None]
        if legacy_weights:
            low, high = min(legacy_weights), max(legacy_weights)
            if low == high:
                low, high = max(Decimal('0'), low - Decimal('2.5')), high + Decimal('2.5')
            scale = {
                'min_kg': (low / Decimal('2.5')).to_integral_value(rounding=ROUND_FLOOR) * Decimal('2.5'),
                'max_kg': (high / Decimal('2.5')).to_integral_value(rounding=ROUND_CEILING) * Decimal('2.5'),
            }

    def xy(point):
        day = point_date(point)
        x = x_left + (x_right - x_left) * max(0, min(90, (day - window_start).days)) / 90
        low = scale['min_kg'] if scale else Decimal('0')
        high = scale['max_kg'] if scale else Decimal('1')
        span = high - low or Decimal('1')
        weight = point.weight_kg or Decimal('0')
        y = baseline_y - float((weight - low) / span) * plot_height
        return round(x, 2), round(y, 2)
    timeline_ticks = []
    for elapsed_days in (0, 30, 60, 90):
        tick_date = window_start + timedelta(days=elapsed_days)
        timeline_ticks.append({
            'x': round(x_left + (x_right - x_left) * elapsed_days / 90, 2),
            'label': tick_date.strftime('%d/%m'),
            'anchor': 'start' if elapsed_days == 0 else ('end' if elapsed_days == 90 else 'middle'),
        })
    points = []
    previous_program_id = None
    for point in weighted:
        x, y = xy(point)
        program_id = getattr(point, 'program_id', '') or ''
        changed = bool(points and program_id and previous_program_id and program_id != previous_program_id)
        points.append({
            'x': x, 'y': y, 'weight_kg': point.weight_kg,
            'performed_on': point.performed_on, 'reps': point.reps, 'rir': point.rir,
            'label': _format_short_date(point.performed_on),
            'is_program_change': changed, 'program_id': program_id,
            'week_in_program': getattr(point, 'week_in_program', None),
        })
        previous_program_id = program_id or previous_program_id

    legacy = []
    for point in legacy_points:
        if point.weight_kg is None:
            continue
        x, y = xy(point)
        legacy.append({
            'x': x, 'y': y, 'label': _format_short_date(point.performed_on),
            'performed_on_iso': point_date(point).isoformat(),
            'performed_on_label': _format_long_date(point.performed_on), 'weight_kg': point.weight_kg,
        })

    points_attr = ' '.join(f"{point['x']},{point['y']}" for point in points)
    area_points_attr = (
        f"{points_attr} {points[-1]['x']},{baseline_y} {points[0]['x']},{baseline_y}" if points else ''
    )
    delta = round(float(points[-1]['weight_kg'] - points[0]['weight_kg']), 2) if len(points) > 1 else None
    has_data = len(points) > 1
    has_legacy_points = bool(legacy)
    latest = snapshot.latest_top_set if snapshot else None
    latest_weight = latest.weight_kg if latest else (points[-1]['weight_kg'] if points else None)
    latest_on = latest.performed_on if latest else (points[-1]['performed_on'] if points else None)
    latest_reps = latest.reps if latest else (points[-1]['reps'] if points else None)
    latest_rir = latest.rir if latest else (points[-1]['rir'] if points else None)
    latest_legacy = legacy[-1] if legacy else None
    if has_data and latest_weight is not None and latest_on is not None:
        accessible_description = (
            f'{len(points)} registros de série principal nos últimos 90 dias. '
            f'Último registro: {number_format(float(latest_weight), decimal_pos=1, use_l10n=True)} kg '
            f'em {_format_short_date(latest_on)}.'
        )
    elif points:
        accessible_description = (
            f'Uma série principal nos últimos 90 dias, em {_format_short_date(points[-1]["performed_on"])}. '
            'Ainda não há pontos suficientes para comparar.'
        )
    elif latest_weight is not None and latest_on is not None:
        accessible_description = (
            'Sem séries principais na janela dos últimos 90 dias. '
            f'Último registro: {number_format(float(latest_weight), decimal_pos=1, use_l10n=True)} kg '
            f'em {_format_short_date(latest_on)}.'
        )
    elif latest_legacy:
        accessible_description = (
            'Histórico anterior salvo, sem classificação. '
            f'Último registro: {number_format(float(latest_legacy["weight_kg"]), decimal_pos=1, use_l10n=True)} kg '
            f'em {latest_legacy["label"]}.'
        )
    elif has_legacy_points or (snapshot and snapshot.has_legacy_history):
        accessible_description = 'Histórico anterior salvo, sem curva comparável de séries principais.'
    else:
        accessible_description = 'Ainda não há série principal para desenhar a curva.'
    return {
        'has_data': has_data,
        'has_chart': has_data,
        'has_latest_top_set': latest is not None,
        'has_recent_points': bool(points),
        'session_points': points,
        'has_session_points': bool(points),
        'has_legacy_history': bool(snapshot and snapshot.has_legacy_history),
        'has_legacy_points': has_legacy_points,
        'viewbox': f'0 0 {_CHART_WIDTH} {_CHART_HEIGHT + 20}',
        'label_y': _CHART_HEIGHT + 15,
        'baseline_y': baseline_y,
        'points_attr': points_attr if has_data else '',
        'area_points_attr': area_points_attr if has_data else '',
        'points': points if has_data else [],
        'legacy_points': legacy,
        'timeline_ticks': timeline_ticks,
        'latest_weight_kg': latest_weight,
        'latest_performed_on': latest_on,
        'latest_reps': latest_reps,
        'latest_rir': latest_rir,
        'latest_legacy_weight_kg': latest_legacy['weight_kg'] if latest_legacy else None,
        'latest_legacy_performed_on_iso': latest_legacy['performed_on_iso'] if latest_legacy else None,
        'latest_legacy_date_label': latest_legacy['performed_on_label'] if latest_legacy else None,
        'accessible_description': accessible_description,
        'delta_weight_kg': delta,
        'trend': _trend(delta or 0),
        'trend_signal': snapshot.trend_signal if snapshot else 'insufficient_data',
        'one_rep_max': snapshot.one_rep_max if snapshot else None,
        'scale_min': scale['min_kg'] if scale else None,
        'scale_max': scale['max_kg'] if scale else None,
    }

@register.simple_tag
def cycle_summary_rows(progress_snapshots: dict, movement_labels: dict | None) -> list[dict]:
    """Visão consolidada do ciclo (1ª das "3 frentes seguintes" citadas em
    curva-grafico-hierarquia-e-set-role.md §0, junto de celebração de PR
    -- já entregue -- e card compartilhável) -- resumo por movimento pra
    não precisar abrir cada card de Evolução de carga pra saber "como
    estou indo neste ciclo".

    NUNCA recalcula nada: cada linha vem do MESMO `ProgressSnapshot` que
    os cards de Evolução/1RM/tendência já usam (`build_progress_snapshots`,
    uma chamada em lote por conta, threada pela view) -- zero query nova,
    zero risco de um número aqui divergir do card detalhado do mesmo
    movimento. Movimento sem nenhum top_set ativo (nunca registrado, ou
    só aquecimento/legado) não aparece -- um resumo com linha vazia não
    ajuda ninguém."""
    rows = []
    for movement_slug, snapshot in (progress_snapshots or {}).items():
        latest = snapshot.latest_top_set
        if latest is None:
            continue
        rows.append({
            'movement_slug': movement_slug,
            'label': resolve_movement_display_name(movement_slug, movement_labels),
            'weight_kg': latest.weight_kg,
            'reps': latest.reps,
            'performed_on': latest.performed_on,
            'trend_signal': snapshot.trend_signal,
            'one_rep_max': snapshot.one_rep_max,
        })
    rows.sort(key=lambda row: row['label'])
    return rows


def _fmt_kg_for_share(value) -> str:
    # Mesmo comportamento de fmtNumber (load_tracker.js): sem zero decimal
    # falso (100 -> "100", nunca "100,0"), vírgula pt-BR. Texto puro (nao
    # passa por {% localize %}) porque share_content_for_chart devolve
    # STRING pronta pro Web Share API, nunca um numero pro template
    # formatar depois.
    return f'{float(value):g}'.replace('.', ',')


@register.simple_tag
def share_content_for_chart(chart: dict, movement_label: str) -> dict:
    """Card compartilhável (3ª frente, ver docstring de cycle_summary_rows)
    -- FUNDAÇÃO decidida com o Renan em 24/09/2026: por agora só texto
    pro Web Share API (`navigator.share`), nunca imagem gerada. Devolve
    `{'title': '', 'text': ''}` (o template some o botão) quando não há
    nada pra compartilhar ainda.

    Por que este formato faz a versão com imagem ficar fácil depois: o
    `chart` recebido aqui é o MESMO dict de `progress_chart_for_movement`
    que já alimenta a tela (nunca uma segunda leitura/cálculo) -- quando
    a versão com imagem existir, ela consome o MESMO `chart`/
    `movement_label` e só ACRESCENTA uma chave nova a este dict (ex.:
    `image_url`), sem mudar a assinatura desta tag. Do lado do JS,
    `wireShareButtons` (load_tracker.js) já lê `data-share-title`/
    `data-share-text` do jeito que vai continuar lendo depois -- só
    ganharia um `data-share-image-url` opcional pra chamar
    `navigator.share({files: [...]})` quando o arquivo existir."""
    weight_kg = chart.get('latest_weight_kg') if chart else None
    if weight_kg is None:
        return {'title': '', 'text': ''}

    parts = [f'{_fmt_kg_for_share(weight_kg)} kg']

    trend_signal = chart.get('trend_signal')
    if trend_signal == 'improving':
        parts.append('em evolução')
    elif trend_signal == 'plateau':
        parts.append('estável')
    elif trend_signal == 'declining':
        parts.append('recuperando de um platô')

    # So' menciona a variacao quando e' GANHO -- "card compartilhavel" e'
    # uma superficie de celebracao (mesmo espirito da Fase 4), nao um
    # extrato neutro. Uma queda no periodo ja aparece via trend_signal
    # ("recuperando de um platô") sem precisar do numero negativo.
    delta = chart.get('delta_weight_kg')
    if delta and delta > 0:
        parts.append(f'+{_fmt_kg_for_share(delta)} kg no período')

    one_rep_max = chart.get('one_rep_max')
    if one_rep_max is not None:
        # Mesmo motivo de progress_eligibility.py::_role_of -- `chart` vem
        # de progress_chart_for_movement, que so' repassa snapshot.one_rep_max
        # como veio: OneRepMaxEstimate (dataclass, producao) OU dict puro
        # (fixture de teste do template, ver test_workout_template.py::_render).
        # Acessar so' por atributo quebraria com AttributeError no segundo caso.
        value_kg = one_rep_max.get('value_kg') if isinstance(one_rep_max, dict) else one_rep_max.value_kg
        parts.append(f'1RM estimado {_fmt_kg_for_share(value_kg)} kg')

    return {
        'title': f'Minha evolução em {movement_label}',
        'text': f'💪 {movement_label}: ' + ' · '.join(parts),
    }


@register.filter
def personal_record(entries: list[dict]) -> dict:
    """Onda B3 — aba "Suas Cargas": maior peso ja registrado de UM
    movimento (mesmo shape de services.list_load_history, ja filtrado
    pro movimento — mesmo uso de `{% regroup %}` que load_chart_points ja
    faz na aba Historico). Diferente de load_chart_points (que mostra
    EVOLUCAO), aqui so o recorde importa — 1 registro so ja e suficiente,
    sem o corte de "2 pontos minimo" daquele filtro.

    Plano curva-grafico-hierarquia-e-set-role.md (§7.5/§8.1 item 4):
    `eligible_for_personal_record` (top_set/max_set) filtra ANTES do
    `max()` — achado real: `max(weighted, key=peso)` sem filtro deixava
    uma serie de aquecimento pesada virar "recorde" por engano.
    `legacy_unknown` nunca elegivel (ver progress_eligibility.py)."""
    eligible = [
        entry for entry in entries
        if entry.get('weight_kg') is not None and eligible_for_personal_record(entry)
    ]
    if not eligible:
        return {'has_data': False, 'weight_kg': None, 'performed_on': None, 'reps': None}

    best = max(eligible, key=lambda entry: entry['weight_kg'])
    return {
        'has_data': True,
        'weight_kg': best['weight_kg'],
        'performed_on': best.get('performed_on'),
        'performed_on_label': _format_long_date(best.get('performed_on')),
        'reps': best.get('reps'),
    }


@register.simple_tag
def personal_record_rows(entries: list[dict], movement_labels: dict | None = None) -> list[dict]:
    """Build only real record rows so the template can render an accurate
    empty state when history contains warmups/legacy entries but no eligible
    personal record. This is an in-memory projection of the already loaded
    history and performs no database query."""
    grouped: dict[str, list[dict]] = {}
    for entry in entries or []:
        slug = entry.get('movement_slug')
        if slug:
            grouped.setdefault(slug, []).append(entry)

    rows = []
    for movement_slug, movement_entries in grouped.items():
        record = personal_record(movement_entries)
        if not record['has_data']:
            continue
        rows.append({
            'movement_slug': movement_slug,
            'label': resolve_movement_display_name(movement_slug, movement_labels),
            **record,
        })
    rows.sort(key=lambda row: row['label'])
    return rows

@register.filter
def periodization_chart_points(periodization: dict | None) -> list[dict]:
    """Pontos do gráfico "Progressão do mesociclo" — de `periodization.weeks`
    (modelo canônico, `periodization.build_chart_points_from_weeks`) quando
    existe; senão o `periodization.chart` legado de sempre, cada ponto com
    `week_number=None` acrescentado (nunca destaca semana pra cliente ainda
    não migrado — não há como saber com segurança qual coluna do `chart`
    livre corresponde à semana de hoje, ver docstring de periodization.py)."""
    if not periodization:
        return []
    weeks = periodization.get('weeks')
    if weeks:
        return build_chart_points_from_weeks(weeks)
    return [dict(point, week_number=None) for point in (periodization.get('chart') or [])]


@register.filter
def current_period_week_number(payload: dict) -> int | None:
    """Wrapper de template pra periodization.current_week_number."""
    return current_week_number(payload)


@register.simple_tag
def current_period_phase(payload: dict):
    """PhaseProfile ativo agora (ou `None`) — computado UMA vez no topo da
    aba Treino (`{% current_period_phase program as phase %}`) e passado
    pra `movement_load_display` de cada movimento, em vez de cada
    movimento recalcular a mesma coisa."""
    return current_phase_profile(payload)


@register.simple_tag
def periodization_phase_banner(payload: dict) -> dict:
    """Banner "Semana 3 de 6 · Força-Hipertrofia — alvo 6-8 reps · RIR 1-2
    · ~76% RM" no topo da aba Treino — só aparece (`visible=True`) quando o
    programa já tem `periodization.weeks` (modelo canônico); `visible=
    False` pros outros clientes, nada muda pra eles."""
    phase = current_phase_profile(payload)
    if phase is None:
        return {'visible': False}

    weeks = (payload.get('periodization') or {}).get('weeks') or []
    return {
        'visible': True,
        'week_number': current_week_number(payload),
        'total_weeks': len(weeks),
        'phase_label': phase.label,
        'reps_min': phase.reps_target_range[0],
        'reps_max': phase.reps_target_range[1],
        'rir_target': phase.rir_target,
        'pct_mid': round(sum(phase.intensity_pct_range) / 2),
    }


def _round_to_nearest_load(value: float) -> float:
    return round(value / 2.5) * 2.5


@register.simple_tag
def todays_logged_weight(load_history: list, movement_slug: str):
    """Último peso registrado hoje, de qualquer papel, para o aviso de salvamento."""
    return _todays_weight(load_history, movement_slug, top_set_only=False)


@register.simple_tag
def todays_top_set_weight(load_history: list, movement_slug: str):
    """Série principal de hoje para preencher o campo cujo papel padrão é top_set."""
    return _todays_weight(load_history, movement_slug, top_set_only=True)


def _todays_weight(load_history: list, movement_slug: str, *, top_set_only: bool):
    today_iso = timezone.localdate().isoformat()
    for entry in reversed(load_history or ()):
        if entry.get('movement_slug') != movement_slug or entry.get('performed_on') != today_iso:
            continue
        if top_set_only and not eligible_for_progress_curve(entry):
            continue
        return entry.get('weight_kg')
    return None


@register.simple_tag
def todays_logged_reps(load_history: list, movement_slug: str):
    """Mesma busca de `todays_logged_weight`, só que devolvendo `reps` —
    par pra pré-preencher o novo campo de repetições com o que já foi
    salvo hoje (plano curva-carga-completa-reps-rir-recorde, Fase 1)."""
    today_iso = timezone.localdate().isoformat()
    for entry in reversed(load_history or ()):
        if entry.get('movement_slug') == movement_slug and entry.get('performed_on') == today_iso:
            return entry.get('reps')
    return None


@register.simple_tag
def todays_logged_rir(load_history: list, movement_slug: str):
    """Mesma busca de `todays_logged_weight`, só que devolvendo `rir`."""
    today_iso = timezone.localdate().isoformat()
    for entry in reversed(load_history or ()):
        if entry.get('movement_slug') == movement_slug and entry.get('performed_on') == today_iso:
            return entry.get('rir')
    return None


@register.simple_tag
def todays_logged_idempotency_key(load_history: list, movement_slug: str):
    """Chave do registro ATIVO de hoje pra este movimento — usada pelo
    cliente como `supersedes_idempotency_key` quando o aluno edita e salva
    de novo (Fase 3 do plano curva-carga-completa-reps-rir-recorde, §4.2):
    "Salvar" sobre um valor já registrado hoje corrige aquele registro, em
    vez de criar uma segunda linha pro mesmo dia. `load_history` já chega
    aqui filtrado por `only_active=True` (ver views), então nunca aponta
    pra um registro já corrigido por outra operação."""
    today_iso = timezone.localdate().isoformat()
    for entry in reversed(load_history or ()):
        if entry.get('movement_slug') == movement_slug and entry.get('performed_on') == today_iso:
            return entry.get('idempotency_key')
    return None


@register.simple_tag
def todays_load_entry(load_history: list, movement_slug: str, set_role: str):
    """Return today's active entry for one explicit role.

    The load widget edits either the top set or a warmup. Keeping these
    targets separate prevents a later warmup from being corrected with the
    top-set value shown in the form (and vice versa)."""
    today_iso = timezone.localdate().isoformat()
    for entry in reversed(load_history or ()):
        if (
            entry.get('movement_slug') == movement_slug
            and entry.get('performed_on') == today_iso
            and entry.get('set_role') == set_role
        ):
            return entry
    return None


@register.simple_tag
def todays_default_load_entry(load_history: list, movement_slug: str):
    """Prefer today's top set for the default form; otherwise use a warmup."""
    top_set = todays_load_entry(load_history, movement_slug, 'top_set')
    return top_set or todays_load_entry(load_history, movement_slug, 'warmup')


@register.simple_tag
def movement_load_display(
    movement: dict, payload: dict, phase, one_rep_max_by_movement: dict, progress_snapshots: dict | None = None
) -> dict:
    """Cascata de exibição de carga do movimento — devolve um dict pronto
    pro template só desenhar (`kind`/`value_kg`/`percentage`/
    `show_registration_hint`), mantendo toda a lógica testável em Python
    (mesmo padrão de `load_chart_points`). Ordem (primeira que resolver
    ganha):

    1. `load_type == 'fixed_kg'` — literal, já é kg.
    2. `load_type == 'percentage_of_rm'` explícito — % + kg calculado
       quando já existe 1RM pro movimento; só a % + hint sem 1RM ainda
       (nunca só a % quando dá pra virar kg — porcentagem sozinha não é
       acionável pro aluno).
    3. Fase canônica ativa (`phase` não é `None`) —
       `periodization.suggest_progressive_load_kg`, ancorado na ÚLTIMA
       carga real registrada nesse movimento (nunca recalcula do zero
       contra 1RM estimado, ver docstring de periodization.py).
       `last_log` vem de `progress_snapshots[movement_slug].latest_top_set`
       (plano curva-grafico-hierarquia-e-set-role.md, §7.5/§8.1 item 5) —
       NUNCA mais escaneia `load_history` bruto por conta própria: até a
       Revisão 6 daquele plano, esta função tinha uma busca de log bruto
       PRÓPRIA (`_last_log_for_movement`), independente do 1RM/build_
       student_package, que continuava contaminada por aquecimento mesmo
       depois deste consumidor "parecer corrigido" — bug real, não
       hipotético.
    4. Sem fase canônica, ou fase canônica sem âncora ainda (bootstrap,
       primeira vez neste movimento) — `load_suggestion.
       suggest_movement_load`, estimativa pontual a partir do próprio
       reps_spec/rir_spec do exercício.
    5. Nada resolveu e não há 1RM nenhum pro movimento — "Livre" + hint de
       registro."""
    movement_slug = movement.get('movement_slug')
    one_rm_estimate = (one_rep_max_by_movement or {}).get(movement_slug)
    one_rep_max_kg = one_rm_estimate.get('value_kg') if one_rm_estimate else None
    has_one_rep_max = one_rep_max_kg is not None

    load_type = movement.get('load_type')
    load_value = movement.get('load_value')

    if load_type == 'fixed_kg':
        return {'kind': 'fixed_kg', 'value_kg': load_value, 'percentage': None, 'show_registration_hint': False}

    if load_type == 'percentage_of_rm' and load_value is not None:
        value_kg = _round_to_nearest_load(load_value / 100 * one_rep_max_kg) if has_one_rep_max else None
        return {
            'kind': 'percentage',
            'value_kg': value_kg,
            'percentage': load_value,
            'show_registration_hint': not has_one_rep_max,
        }

    if phase is not None:
        # Plano curva-grafico-hierarquia-e-set-role.md (§7.5/§8.1 item 5)
        # -- bug real achado na Revisao 6: _last_log_for_movement fazia
        # uma busca de log BRUTO propria, independente do 1RM/snapshot, e
        # nao se corrigia junto quando build_student_package passou a
        # filtrar por set_role. Agora le progress_snapshot.latest_top_set
        # (ja' elegivel -- so' top_set real, nunca aquecimento).
        # suggest_progressive_load_kg espera um dict (`.get(...)`), nao o
        # dataclass ProgressPoint -- conversao local, sem mudar
        # periodization.py.
        snapshot = (progress_snapshots or {}).get(movement_slug)
        latest_top_set = snapshot.latest_top_set if snapshot else None
        last_log = (
            {
                'weight_kg': latest_top_set.weight_kg,
                'reps': latest_top_set.reps,
                'rir': latest_top_set.rir,
                'performed_on': latest_top_set.performed_on.isoformat(),
                'program_id': latest_top_set.program_id,
            }
            if latest_top_set is not None else None
        )
        value_kg = suggest_progressive_load_kg(
            payload=payload, current_phase=phase, last_log=last_log, one_rep_max_kg=one_rep_max_kg,
        )
        if value_kg is not None:
            return {
                'kind': 'phase_progressive',
                'value_kg': value_kg,
                'percentage': round(sum(phase.intensity_pct_range) / 2),
                'show_registration_hint': False,
            }

    suggestion = suggest_movement_load(movement=movement, one_rep_max_kg=one_rep_max_kg)
    if suggestion is not None:
        return {
            'kind': 'rir_estimate',
            'value_kg': suggestion['value_kg'],
            'percentage': None,
            'show_registration_hint': False,
        }

    return {'kind': 'free', 'value_kg': None, 'percentage': None, 'show_registration_hint': not has_one_rep_max}
