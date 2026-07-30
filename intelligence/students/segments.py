"""
ARQUIVO: segmento do aluno como regra transparente versionada (Onda 7).

POR QUE ELE EXISTE:
- Student.status e ciclo de vida (lead/active/paused/inactive), nao
  segmento. Sem segmento, nao da pra perguntar "que tipo de aluno fica" —
  so "quantos ficam". Este modulo classifica o aluno em um segment_key de
  baixa cardinalidade, por regra explicita (nao clustering opaco), fechando
  o loop canal -> conversao -> segmento -> retencao/churn descrito no
  plano pai (docs/plans/leads-ml-foundation-and-network-intelligence-plan.md).

O QUE ESTE ARQUIVO FAZ:
1. classifica ciclo de cobranca, comportamento de pagamento e faixa etaria.
2. monta segment_key = 'ciclo|comportamento_pagamento|faixa_etaria'.

PONTOS CRITICOS:
- NAO grava no model Student — leitura derivada, recalculada sob demanda,
  nunca persistida como verdade primaria.
- NAO usa clustering opaco nesta fase — so regra explicita e versionada
  (rule_version), para o dono conseguir explicar cada rotulo sem depender
  de um modelo estatistico.
- canal resolvido (Student.resolved_acquisition_source) fica FORA do
  segment_key de proposito: ja existe como campo proprio no Student e serve
  para ser lido ao lado do segmento (ex: "instagram" x "trimestral|pontual|
  30-39"), nao amassado dentro da mesma string — meter tudo numa string so
  faria a cardinalidade explodir sem necessidade.
- este modulo nao consulta o banco: recebe latest_enrollment e
  payments_queryset ja resolvidos pelo chamador, para nao criar dependencia
  de intelligence/ sobre camadas de apresentacao (catalog/).
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from finance.overdue_metrics import get_overdue_payments_queryset

RULE_VERSION = 'student_segment_v1'
RECURRING_LATE_THRESHOLD = 2
AGE_BAND_WIDTH = 10
NO_PLAN_LABEL = 'sem_plano'
NO_AGE_LABEL = 'sem_idade'


@dataclass(frozen=True, slots=True)
class StudentSegment:
    segment_key: str
    billing_cycle: str
    payment_behavior: str
    age_band: str
    rule_version: str


def _resolve_age_band(*, birth_date, today):
    if birth_date is None:
        return NO_AGE_LABEL
    had_birthday_this_year = (today.month, today.day) >= (birth_date.month, birth_date.day)
    age = today.year - birth_date.year - (0 if had_birthday_this_year else 1)
    if age < 0:
        return NO_AGE_LABEL
    floor = (age // AGE_BAND_WIDTH) * AGE_BAND_WIDTH
    return f'{floor}-{floor + AGE_BAND_WIDTH - 1}'


def _resolve_payment_behavior(*, payments_queryset, today):
    total_payments = payments_queryset.count()
    if total_payments == 0:
        return 'sem_historico'
    overdue_count = get_overdue_payments_queryset(payments_queryset, today=today).count()
    if overdue_count >= RECURRING_LATE_THRESHOLD:
        return 'atrasado_recorrente'
    if overdue_count == 1:
        return 'atraso_pontual'
    return 'pontual'


def resolve_student_segment(*, student, latest_enrollment=None, payments_queryset=None, today=None) -> StudentSegment:
    """Classifica o aluno em um segmento transparente e versionado.

    latest_enrollment: Enrollment mais recente do aluno (opcional; se
    ausente, ciclo de cobranca vira 'sem_plano' — aluno sem matricula
    ativa ainda nao tem ciclo para classificar).
    payments_queryset: queryset de Payment do aluno (opcional; se ausente,
    usa student.payments.all()).
    """
    resolved_today = today or timezone.localdate()
    billing_cycle = (
        latest_enrollment.plan.billing_cycle
        if latest_enrollment is not None and getattr(latest_enrollment, 'plan', None) is not None
        else NO_PLAN_LABEL
    )
    queryset = payments_queryset if payments_queryset is not None else student.payments.all()
    payment_behavior = _resolve_payment_behavior(payments_queryset=queryset, today=resolved_today)
    age_band = _resolve_age_band(birth_date=student.birth_date, today=resolved_today)

    segment_key = f'{billing_cycle}|{payment_behavior}|{age_band}'
    return StudentSegment(
        segment_key=segment_key,
        billing_cycle=billing_cycle,
        payment_behavior=payment_behavior,
        age_band=age_band,
        rule_version=RULE_VERSION,
    )


__all__ = [
    'AGE_BAND_WIDTH',
    'NO_AGE_LABEL',
    'NO_PLAN_LABEL',
    'RECURRING_LATE_THRESHOLD',
    'RULE_VERSION',
    'StudentSegment',
    'resolve_student_segment',
]
