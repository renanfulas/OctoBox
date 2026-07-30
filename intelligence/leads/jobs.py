"""
ARQUIVO: orquestracao idempotente do feature layer de leads (Onda 6).

POR QUE ELE EXISTE:
- busca os dados (unico lugar desta capacidade que toca o banco) e persiste
  o resultado do calculo puro (features.py) via upsert, para rodar 2x
  produzir as mesmas contagens sem duplicar linha.

PONTOS CRITICOS:
- coorte com janela de maturacao: so entram leads criados ATE
  hoje - maturation_days. Lead de ontem nao e lead perdido — e censura a
  direita (ver docs/plans/leads-ml-technical-execution-guide.md, Onda 6).
- ML nunca escreve verdade primaria: esta funcao so LE StudentIntake e
  escreve em LeadChannelDailyFact — nunca em StudentIntake/Student.
"""

from __future__ import annotations

from django.utils import timezone

from intelligence.leads.features import compute_lead_channel_facts
from intelligence.models import LeadChannelDailyFact
from onboarding.models import StudentIntake

RULE_VERSION = 'lead_channel_facts_v1'
DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_MATURATION_DAYS = 30


def _fetch_intake_rows(*, window_start, window_end):
    return list(
        StudentIntake.objects.filter(
            created_at__date__gte=window_start,
            created_at__date__lte=window_end,
        ).values('phone_lookup_index', 'created_at', 'status', 'converted_at', 'source', 'raw_payload')
    )


def compute_and_persist_lead_channel_facts(
    *,
    today=None,
    lookback_days=DEFAULT_LOOKBACK_DAYS,
    maturation_days=DEFAULT_MATURATION_DAYS,
    rule_version=RULE_VERSION,
):
    """Idempotente: chamar 2x sobre o mesmo banco produz as mesmas
    contagens (so computed_at muda — upsert por window_start+channel+
    provenance+rule_version, nunca cria linha duplicada).
    """
    reference_today = today or timezone.localdate()
    window_end = reference_today - timezone.timedelta(days=maturation_days)
    window_start = window_end - timezone.timedelta(days=lookback_days)
    computed_at = timezone.now()
    input_window = f'{lookback_days}d'

    rows = _fetch_intake_rows(window_start=window_start, window_end=window_end)
    facts = compute_lead_channel_facts(
        rows=rows,
        rule_version=rule_version,
        input_window=input_window,
        window_start=window_start,
        window_end=window_end,
        computed_at=computed_at,
    )

    persisted = 0
    for fact in facts:
        LeadChannelDailyFact.objects.update_or_create(
            window_start=fact['window_start'],
            channel=fact['channel'],
            provenance=fact['provenance'],
            rule_version=fact['rule_version'],
            defaults={
                'window_end': fact['window_end'],
                'captured_total': fact['captured_total'],
                'converted_total': fact['converted_total'],
                'rejected_total': fact['rejected_total'],
                'open_total': fact['open_total'],
                'median_days_to_conversion': fact['median_days_to_conversion'],
                'computed_at': fact['computed_at'],
                'input_window': fact['input_window'],
            },
        )
        persisted += 1

    return {
        'window_start': window_start,
        'window_end': window_end,
        'cells_persisted': persisted,
        'rule_version': rule_version,
        'computed_at': computed_at,
    }


__all__ = [
    'DEFAULT_LOOKBACK_DAYS',
    'DEFAULT_MATURATION_DAYS',
    'RULE_VERSION',
    'compute_and_persist_lead_channel_facts',
]
