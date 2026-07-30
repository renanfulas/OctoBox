"""
ARQUIVO: leitura de benchmark de rede por cohort/canal (Onda 8).

POR QUE ELE EXISTE:
- compara a leitura local da box com a mediana do MESMO cohort, nunca com
  a rede inteira (boxes heterogeneas produzem prior enganoso).
- so publica se pelo menos MIN_BOXES_FOR_BENCHMARK boxes DISTINTAS
  contribuiram para a celula — protege contra inferir uma box individual
  a partir do "benchmark" (k-anonimato a nivel de leitura, nao so de
  contribuicao).

PONTOS CRITICOS:
- retorna None (suprimido) quando faltar amostra — nunca zero, que seria
  lido como "essa origem nao converte", uma afirmacao factualmente falsa.
- so esta onda: leitura comparativa. Nenhum prior aplicado ainda (isso e
  Onda 9).
"""

from __future__ import annotations

import statistics

from django.utils import timezone

from intelligence_network.models import NetworkChannelAggregate
from intelligence_network.shrinkage import DEFAULT_PRIOR_WEIGHT, apply_shrinkage

DEFAULT_MIN_BOXES_FOR_BENCHMARK = 5
DEFAULT_MAX_STALENESS_DAYS = 45


def resolve_channel_benchmark(
    *,
    box_cohort,
    channel,
    window,
    min_boxes=DEFAULT_MIN_BOXES_FOR_BENCHMARK,
    max_staleness_days=DEFAULT_MAX_STALENESS_DAYS,
    now=None,
):
    """Retorna a mediana de taxa de conversao do cohort para o canal e
    janela pedidos, ou None se menos de min_boxes boxes distintas
    contribuiram (celula suprimida, nao zerada).

    Contribuicao mais velha que max_staleness_days e ignorada: prior
    desatualizado (ex: canal que decaiu) nao pode continuar influenciando
    a leitura ajustada so porque ninguem rodou o job de contribuicao de
    novo — expira, nao acumula (input_window rolante).
    """
    reference_now = now or timezone.now()
    cutoff = reference_now - timezone.timedelta(days=max_staleness_days)
    rows = list(
        NetworkChannelAggregate.objects.filter(
            box_cohort=box_cohort,
            channel=channel,
            window=window,
            contributed_at__gte=cutoff,
        ).values('box_slug', 'captured_total', 'converted_total')
    )
    distinct_boxes = {row['box_slug'] for row in rows}
    if len(distinct_boxes) < min_boxes:
        return None

    rates = [
        round((row['converted_total'] / row['captured_total']) * 100, 1)
        for row in rows
        if row['captured_total'] > 0
    ]
    if not rates:
        return None

    return {
        'box_cohort': box_cohort,
        'channel': channel,
        'window': window,
        'median_conversion_rate': round(statistics.median(rates), 1),
        'box_count': len(distinct_boxes),
    }


def resolve_channel_reading_with_network_prior(
    *,
    box_cohort,
    channel,
    window,
    local_captured_total,
    local_converted_total,
    prior_weight=DEFAULT_PRIOR_WEIGHT,
    min_boxes=DEFAULT_MIN_BOXES_FOR_BENCHMARK,
    max_staleness_days=DEFAULT_MAX_STALENESS_DAYS,
    now=None,
):
    """Leitura ajustada por shrinkage (Onda 9): comeca no prior da rede
    (cold start, box nova) e converge para o dado local conforme
    local_captured_total cresce.

    Retorna None quando nao ha prior publicavel (celula do cohort abaixo
    do piso k, ou so com contribuicao expirada) — nesse caso o chamador
    deve usar so a leitura local, sem ajuste, e nao fingir que existe uma
    rede que ainda nao tem volume ou que ja ficou desatualizada.
    """
    benchmark = resolve_channel_benchmark(
        box_cohort=box_cohort,
        channel=channel,
        window=window,
        min_boxes=min_boxes,
        max_staleness_days=max_staleness_days,
        now=now,
    )
    if benchmark is None:
        return None

    local_rate = (
        round((local_converted_total / local_captured_total) * 100, 1)
        if local_captured_total > 0
        else 0.0
    )
    adjusted_rate = apply_shrinkage(
        local_rate=local_rate,
        local_n=local_captured_total,
        prior_rate=benchmark['median_conversion_rate'],
        prior_weight=prior_weight,
    )
    return {
        'local_rate': local_rate,
        'local_captured_total': local_captured_total,
        'network_prior_rate': benchmark['median_conversion_rate'],
        'network_box_count': benchmark['box_count'],
        'adjusted_rate': adjusted_rate,
        'is_network_prior': local_captured_total == 0,
        'prior_weight': prior_weight,
    }


__all__ = [
    'DEFAULT_MAX_STALENESS_DAYS',
    'DEFAULT_MIN_BOXES_FOR_BENCHMARK',
    'resolve_channel_benchmark',
    'resolve_channel_reading_with_network_prior',
]
