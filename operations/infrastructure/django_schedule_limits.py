"""
ARQUIVO: limites operacionais da agenda de aulas.

POR QUE ELE EXISTE:
- isola a validacao de volume da agenda em um adapter Django reutilizavel.

O QUE ESTE ARQUIVO FAZ:
1. usa faixas puras semanal e mensal vindas do dominio.
2. conta aulas ativas por dia, semana e mes.
3. bloqueia criacoes ou edicoes acima dos limites operacionais.

PONTOS CRITICOS:
- os contadores nao podem dobrar pendencias quando a criacao ja persiste item por item.
"""

from operations.domain import get_month_bounds, get_week_bounds
from operations.models import ClassSession, SessionStatus


DAILY_SESSION_LIMIT = 12
WEEKLY_SESSION_LIMIT = 70
MONTHLY_SESSION_LIMIT = 150
def _build_active_session_queryset(*, exclude_session_ids=None):
    queryset = ClassSession.objects.exclude(status=SessionStatus.CANCELED)
    if exclude_session_ids:
        queryset = queryset.exclude(pk__in=exclude_session_ids)
    return queryset


def ensure_schedule_limits(*, scheduled_date, exclude_session_ids=None, pending_day=0, pending_week=0, pending_month=0):
    active_sessions = _build_active_session_queryset(exclude_session_ids=exclude_session_ids)
    week_start, week_end = get_week_bounds(scheduled_date)
    month_start, month_end = get_month_bounds(scheduled_date)

    day_count = active_sessions.filter(scheduled_at__date=scheduled_date).count()
    week_count = active_sessions.filter(scheduled_at__date__gte=week_start, scheduled_at__date__lte=week_end).count()
    month_count = active_sessions.filter(scheduled_at__date__gte=month_start, scheduled_at__date__lte=month_end).count()

    if day_count + pending_day >= DAILY_SESSION_LIMIT:
        raise ValueError(f'Limite diario atingido: o box aceita no maximo {DAILY_SESSION_LIMIT} aulas por dia.')
    if week_count + pending_week >= WEEKLY_SESSION_LIMIT:
        raise ValueError(f'Limite semanal atingido: o box aceita no maximo {WEEKLY_SESSION_LIMIT} aulas por semana.')
    if month_count + pending_month >= MONTHLY_SESSION_LIMIT:
        raise ValueError(f'Limite mensal atingido: o box aceita no maximo {MONTHLY_SESSION_LIMIT} aulas por mes.')


__all__ = [
    'DAILY_SESSION_LIMIT',
    'MONTHLY_SESSION_LIMIT',
    'WEEKLY_SESSION_LIMIT',
    'ensure_schedule_limits',
    'get_month_bounds',
    'get_week_bounds',
]