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
"""

from __future__ import annotations

import re

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def humanize_movement_slug(movement_slug: str) -> str:
    """'agachamento-livre' -> 'Agachamento livre'. Mesmo palpite de
    services.py::_ensure_movements_exist — nao consulta PublicWorkoutMovement
    (o template pode receber um payload que ainda nem foi publicado)."""
    if not movement_slug:
        return ''
    return movement_slug.replace('-', ' ').capitalize()


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


@register.filter
def personal_record(entries: list[dict]) -> dict:
    """Onda B3 — aba "Suas Cargas": maior peso ja registrado de UM
    movimento (mesmo shape de services.list_load_history, ja filtrado
    pro movimento — mesmo uso de `{% regroup %}` que load_chart_points ja
    faz na aba Historico). Diferente de load_chart_points (que mostra
    EVOLUCAO), aqui so o recorde importa — 1 registro so ja e suficiente,
    sem o corte de "2 pontos minimo" daquele filtro."""
    weighted = [entry for entry in entries if entry.get('weight_kg') is not None]
    if not weighted:
        return {'has_data': False, 'weight_kg': None, 'performed_on': None, 'reps': None}

    best = max(weighted, key=lambda entry: entry['weight_kg'])
    return {
        'has_data': True,
        'weight_kg': best['weight_kg'],
        'performed_on': best.get('performed_on'),
        'reps': best.get('reps'),
    }


# Vocabulario fechado, extraido das 10 paginas legadas (.st-p/.st-f/.st-t/.st-m
# — ver docs/plans/public-workouts-produtizacao-corda.md, nota da Onda B3):
# cada autor de plano escrevia um rotulo um pouco diferente pro mesmo estagio
# ("Top Set" vs "Top 1/2/3", "Max Set" vs "AMRAP") — normaliza pra 4
# categorias fixas em vez de uma cor por plano, como era antes.
_SET_STAGE_PATTERN = re.compile(
    r'(?P<prefix>\d+(?:-\d+)?×\s*)'
    r'(?P<stage>Prepara(?:t[oó]ria|t\.)?|Prep|Feeder|Top(?:\s*\d+)?(?:\s*Set)?|Max(?:\s*Set)?|AMRAP)',
    re.IGNORECASE,
)


def _set_stage_category(stage_text: str) -> str:
    lowered = stage_text.strip().lower()
    if lowered.startswith('prep'):
        return 'prep'
    if lowered.startswith('feeder'):
        return 'feeder'
    if lowered.startswith('top'):
        return 'top'
    return 'max'  # max/amrap


@register.filter
def highlight_set_stages(reps_spec: str) -> str:
    """Onda B3 — legenda de tipo de serie (Preparatória/Feeder/Top Set/Max
    Set), sem campo novo em schema.py (contrato da Onda S0, D.5 — muda so
    com acordo das duas frentes). `reps_spec` ja carrega o estagio como
    TEXTO livre (ex. "2-3× Prep → 1× Feeder → 3× Top (6-8)", um segmento
    por estagio dentro do mesmo movimento) — este filtro so pinta a
    palavra-chave que ja esta la, nao inventa dado novo. Segmento que nao
    bate o padrao (cardio, HIIT — sem conceito de estagio) sai sem marcacao,
    so o texto original escapado.

    Alvo de `highlight_set_stages` e' HTML de proposito (`mark_safe` via
    format_html) — quem escreve `reps_spec` e o parser do repo (migrate_legacy_workouts),
    nunca input de aluno, mas escapa a mesma forma pra nao depender disso."""
    if not reps_spec:
        return ''

    parts = []
    for segment in reps_spec.split(' → '):
        match = _SET_STAGE_PATTERN.search(segment)
        if not match:
            parts.append(escape(segment))
            continue

        category = _set_stage_category(match.group('stage'))
        before = escape(segment[: match.start()])
        after = escape(segment[match.end() :])
        badge = format_html(
            '<span class="workout-set-stage workout-set-stage--{}">{}</span>',
            category,
            match.group('stage'),
        )
        parts.append(format_html('{}{}{}{}', before, escape(match.group('prefix')), badge, after))

    return mark_safe(' → '.join(str(part) for part in parts))
