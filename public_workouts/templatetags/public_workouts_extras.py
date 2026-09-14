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

from datetime import date as _date

from django import template
from django.utils import timezone

from public_workouts.dashboard import build_program_summary, build_week_overview

register = template.Library()


@register.simple_tag
def program_summary(payload: dict) -> dict:
    """Wrapper de template pra dashboard.build_program_summary — o template
    so tem `program` (o payload) no contexto, nao precisa de var nova."""
    return build_program_summary(payload)


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
