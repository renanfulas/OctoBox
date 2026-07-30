"""
ARQUIVO: contribuicao por box ao hub de rede (Onda 8).

POR QUE ELE EXISTE:
- cada box contribui SO agregados (nunca linha individual de aluno/lead)
  para o schema public, onde o benchmark cross-tenant pode ler.

O QUE ESTE ARQUIVO FAZ:
1. le o feature layer local do box (LeadChannelDailyFact, Onda 6).
2. resolve o cohort do box (porte por alunos ativos).
3. contribui (upsert) cada celula com amostra suficiente para
   NetworkChannelAggregate — SHARED, resolve para o schema public mesmo
   chamado de dentro do schema_context de um tenant.

PONTOS CRITICOS:
- roda dentro do schema_context de cada box (via shared_support.tenant_sweep,
  Onda 1) — StudentIntake/LeadChannelDailyFact (TENANT) resolvem para o box;
  NetworkChannelAggregate (SHARED) resolve para public. Postgres faz isso
  sozinho via search_path (box_x, public).
- celula com captured_total abaixo do piso NAO e contribuida — protege
  contra subir amostra tao pequena que vira quase-identificacao.
- dado cru NUNCA sobe: so channel + contagem. Nenhum nome, telefone,
  email ou payload individual.
"""

from __future__ import annotations

from django.utils import timezone

from intelligence.models import LeadChannelDailyFact
from intelligence_network.cohort import resolve_box_cohort
from intelligence_network.models import NetworkChannelAggregate
from students.models import Student, StudentStatus

DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE = 10


def _resolve_window_label(*, window_start, window_end):
    return f'{window_start.isoformat()}:{window_end.isoformat()}'


def contribute_box_channel_aggregates(*, box, min_captured_to_contribute=DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE):
    """Contribui as celulas de canal do feature layer local deste box para
    o hub de rede. Retorna quantas celulas foram contribuidas.
    """
    active_student_count = Student.objects.filter(status=StudentStatus.ACTIVE).count()
    box_cohort = resolve_box_cohort(active_student_count=active_student_count)
    contributed_at = timezone.now()

    contributed = 0
    for fact in LeadChannelDailyFact.objects.exclude(channel=''):
        if fact.captured_total < min_captured_to_contribute:
            continue

        NetworkChannelAggregate.objects.update_or_create(
            box_slug=box.slug,
            channel=fact.channel,
            window=_resolve_window_label(window_start=fact.window_start, window_end=fact.window_end),
            defaults={
                'box_cohort': box_cohort,
                'segment_key': '',
                'captured_total': fact.captured_total,
                'converted_total': fact.converted_total,
                'retained_90d_total': 0,
                'k_floor_applied': min_captured_to_contribute,
                'contributed_at': contributed_at,
            },
        )
        contributed += 1
    return contributed


__all__ = ['DEFAULT_MIN_CAPTURED_TO_CONTRIBUTE', 'contribute_box_channel_aggregates']
