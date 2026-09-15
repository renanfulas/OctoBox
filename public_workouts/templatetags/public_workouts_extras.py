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
from datetime import date as _date

from django import template
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe

from public_workouts.dashboard import build_program_summary, build_week_overview, day_keyword, day_short_label

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
    return build_week_overview(payload=payload, completed_dates=completed_dates)


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
def movement_display_name(movement: dict) -> str:
    """Nome pra exibir na tela: `name` (portugues, escrito pelo treinador —
    aditivo, ver schema.py) quando presente; senao humaniza `movement_slug`
    (movimento publicado ANTES desta fatia, sem `name` no payload ainda —
    tambem cobre o fallback ja existente de slug sem wiki-btn, que usa
    slugify(nome) e perderia acento/maiuscula mesmo tendo nome capturado)."""
    name = (movement or {}).get('name')
    if name:
        return name
    return humanize_movement_slug((movement or {}).get('movement_slug', ''))


_GLOSSARY_TERMS = {
    'rir': ('RIR (Reps in Reserve)', 'Repetições que ainda sobrariam na reserva se a série continuasse até a falha. Ex.: RIR 2 = parou a 2 repetições da falha.'),
    'amrap': ('AMRAP (As Many Reps As Possible)', 'Fazer o máximo de repetições possível na série, dentro da técnica segura.'),
    'feeder': ('Série Feeder', 'Série leve de ativação antes da série principal (Top) — prepara a articulação e o padrão de movimento sem gerar fadiga.'),
    'top': ('Série Top (Top Set)', 'A série mais pesada do exercício no dia — o estímulo-alvo do treino, feita depois do aquecimento/feeder.'),
    'prep': ('Série Prep (preparatória)', 'Série de aquecimento específico com carga leve/moderada, antes das séries de trabalho.'),
}

_GLOSSARY_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(term) for term in _GLOSSARY_TERMS) + r')\b',
    re.IGNORECASE,
)


@register.filter
def glossary_highlight(text: str):
    """Marca termos de jargao de treino (RIR, AMRAP, Feeder, Top, Prep) dentro
    de reps_spec/rir_spec (texto livre do treinador, schema.py) com uma
    'bolinha' clicavel que revela a definicao — pedido do Renan pra quem
    nao conhece o dicionario de treino.

    So estes 5 termos: sao os que realmente aparecem nos 10 programas reais
    publicados (conferido via payload, nao adivinhado) — nao generaliza pra
    qualquer palavra tecnica, que arriscaria falso-positivo (ex. 'top' dentro
    de 'topo' e' evitado com \\b, mas uma lista maior sem curadoria arriscaria
    marcar termo errado como se fosse dicionario de treino).

    Retorna SafeString: escapa o texto ao redor, so o termo casado vira HTML.
    """
    if not text:
        return ''

    pieces = []
    last_end = 0
    for match in _GLOSSARY_PATTERN.finditer(text):
        pieces.append(escape(text[last_end:match.start()]))
        term = match.group(0)
        label, description = _GLOSSARY_TERMS[term.lower()]
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
def reps_phases(reps_spec: str):
    """Quebra `reps_spec` em fases (Prep/Feeder/Top/AMRAP) quando o texto do
    treinador junta varias com ' → ' (ex.: '2-3× Prep → 1× Feeder → 3× Top
    (6-8)', formato de `gym-reps` nos 8 dos 10 templates legados que tem
    esse padrao — ver parser.py). Devolve lista de dicts {text, phase} pro
    template desenhar um "chip" colorido por fase (pedido do Renan: "voltar
    o padrao de feeder/topset/amrap"), ou lista VAZIA quando so' ha 1 fase —
    nesse caso o template mantem a linha simples de sempre (nao vale a pena
    um chip grande pra 'reps_spec': '3x12', a maioria dos movimentos sem
    quebra de fase).

    Cada `text` ja passa por glossary_highlight (SafeString) — o template
    nao precisa aplicar o filtro de novo.
    """
    if not reps_spec:
        return []
    segments = [segment.strip() for segment in reps_spec.split('→') if segment.strip()]
    if len(segments) < 2:
        return []
    return [{'text': glossary_highlight(segment), 'phase': _detect_phase(segment)} for segment in segments]


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


def _format_short_date(iso_date: str) -> str:
    """'2026-01-05' -> '05/01'. Rotulo compacto de eixo do mini-grafico —
    nao e' formatacao de data generica do app (list_program_versions, por
    exemplo, deixa a data ISO crua de proposito, pra outro uso)."""
    parts = iso_date.split('-')
    if len(parts) != 3:
        return iso_date
    _year, month, day = parts
    return f'{day}/{month}'


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
    weighted = [entry for entry in entries if entry.get('weight_kg') is not None]
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
