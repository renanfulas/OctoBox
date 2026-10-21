"""Uma leitura SQL para os indicadores de execução do Curva."""

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import PublicWorkoutTrainingSession


def training_summary(*, window_days: int, at=None) -> dict:
    at = at or timezone.now()
    completed = Q(completed_at__isnull=False, completed_at__lte=at)
    partial = Q(outcome='partial', ended_at__isnull=False, ended_at__lte=at)
    cancelled = Q(outcome='cancelled', ended_at__isnull=False, ended_at__lte=at)
    # Estado operacional derivado: comandos offline tardios ainda podem encerrar
    # a sessão sem exigir um cron que a feche antes da sincronização.
    abandoned = Q(outcome='abandoned') | Q(ended_at__isnull=True, started_at__lte=at - timedelta(hours=72))
    numbers = PublicWorkoutTrainingSession.objects.filter(
        started_at__gte=at - timedelta(days=window_days), started_at__lte=at,
    ).aggregate(
        started=Count('pk'),
        completed=Count('pk', filter=completed),
        partial=Count('pk', filter=partial),
        cancelled=Count('pk', filter=cancelled),
        abandoned=Count('pk', filter=abandoned),
        sets=Sum('completed_set_count', filter=completed),
        partial_sets=Sum('completed_set_count', filter=partial),
    )
    started = numbers['started'] or 0
    finished = numbers['completed'] or 0
    return {
        'sessions_started': started,
        'sessions_completed': finished,
        'sessions_partial': numbers['partial'] or 0,
        'sessions_cancelled': numbers['cancelled'] or 0,
        'sessions_abandoned': numbers['abandoned'] or 0,
        'sets_completed': numbers['sets'] or 0,
        'sets_partial': numbers['partial_sets'] or 0,
        'completion_ratio': round(finished / started, 4) if started else None,
        'completion_percent': round(finished * 100 / started, 1) if started else None,
        'window_days': window_days,
    }


def recent_training_sessions(*, window_days: int, limit: int = 20, account_id=None, at=None) -> list[dict]:
    at = at or timezone.now()
    queryset = PublicWorkoutTrainingSession.objects.filter(
        started_at__gte=at - timedelta(days=window_days), started_at__lte=at,
    )
    if account_id is not None:
        queryset = queryset.filter(account_id=account_id)
    rows = queryset.annotate(recorded_set_count=Count('sets', filter=Q(sets__status='performed'))).order_by('-started_at').values(
        'id', 'account_id', 'account__email', 'program__version', 'plan_slug', 'day_id',
        'started_at', 'completed_at', 'ended_at', 'outcome', 'recorded_set_count',
    )[:limit]
    labels = {'partial': 'Parcial', 'completed': 'Concluído', 'cancelled': 'Cancelado', 'abandoned': 'Abandonado'}
    return [
        {**row, 'status': labels.get(row['outcome'],
            'Sem encerramento há 72h' if row['ended_at'] is None and row['started_at'] <= at - timedelta(hours=72)
            else 'Em andamento')}
        for row in rows
    ]
