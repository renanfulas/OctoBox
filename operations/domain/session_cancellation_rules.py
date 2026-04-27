"""
ARQUIVO: regras puras de cancelamento de sessao.

POR QUE ELE EXISTE:
- decide quando um cancelamento de aula deve gerar notificacao para alunos com reserva.
- decide qual variante de copy o payload de push deve usar.
- mantem a logica fora de adapters Django e fora de push_notifications.

O QUE ESTE ARQUIVO FAZ:
1. define a decisao de notificacao como dataclass imutavel.
2. expoe should_notify_cancellation() — funcao pura, sem I/O, testavel em ms.
3. expoe resolve_copy_variant() — classifica o contexto em uma das tres variantes.

PONTOS CRITICOS:
- sem imports Django, sem ORM, sem pywebpush, sem settings.
- status strings sao literais; comparar com SessionStatus.CANCELED em infra, nao aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CopyVariant = Literal['ahead', 'last_minute', 'already_checked_in']

# Limiar em minutos: cancelamentos abaixo deste valor sao considerados "em cima da hora".
LAST_MINUTE_THRESHOLD_MINUTES = 120

CANCELED_STATUS = 'canceled'


@dataclass(frozen=True, slots=True)
class CancellationDecision:
    should_notify: bool
    copy_variant: CopyVariant | None


def should_notify_cancellation(
    *,
    prev_status: str,
    new_status: str,
    attendance_count_active: int,
) -> bool:
    """
    Retorna True quando a transicao de status configura um cancelamento notificavel.

    Regras:
    - novo status deve ser 'canceled'.
    - status anterior nao pode ja ser 'canceled' (idempotencia: nao renotifica).
    - deve haver pelo menos 1 presenca ativa (BOOKED ou CHECKED_IN).
    """
    if new_status != CANCELED_STATUS:
        return False
    if prev_status == CANCELED_STATUS:
        return False
    return attendance_count_active > 0


def resolve_copy_variant(
    *,
    cancel_lead_minutes: int,
    had_checked_in_attendance: bool,
) -> CopyVariant:
    """
    Classifica o contexto do cancelamento em uma das tres variantes de copy:

    - 'already_checked_in': algum aluno ja fez check-in (pior caso — estava no box ou indo).
    - 'last_minute': cancelamento com menos de LAST_MINUTE_THRESHOLD_MINUTES de antecedencia.
    - 'ahead': cancelamento com antecedencia suficiente.
    """
    if had_checked_in_attendance:
        return 'already_checked_in'
    if cancel_lead_minutes < LAST_MINUTE_THRESHOLD_MINUTES:
        return 'last_minute'
    return 'ahead'


def build_cancellation_decision(
    *,
    prev_status: str,
    new_status: str,
    attendance_count_active: int,
    cancel_lead_minutes: int,
    had_checked_in_attendance: bool,
) -> CancellationDecision:
    """Ponto de entrada principal: avalia e classifica o cancelamento em uma unica chamada."""
    if not should_notify_cancellation(
        prev_status=prev_status,
        new_status=new_status,
        attendance_count_active=attendance_count_active,
    ):
        return CancellationDecision(should_notify=False, copy_variant=None)

    variant = resolve_copy_variant(
        cancel_lead_minutes=cancel_lead_minutes,
        had_checked_in_attendance=had_checked_in_attendance,
    )
    return CancellationDecision(should_notify=True, copy_variant=variant)


__all__ = [
    'CANCELED_STATUS',
    'LAST_MINUTE_THRESHOLD_MINUTES',
    'CancellationDecision',
    'CopyVariant',
    'build_cancellation_decision',
    'resolve_copy_variant',
    'should_notify_cancellation',
]
