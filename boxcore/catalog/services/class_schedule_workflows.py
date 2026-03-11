"""
ARQUIVO: workflows de criacao recorrente da grade de aulas.

POR QUE ELE EXISTE:
- Tira da view a logica de gerar aulas recorrentes, validar limites e registrar auditoria.

O QUE ESTE ARQUIVO FAZ:
1. Gera aulas em serie a partir de um intervalo e dias da semana.
2. Evita duplicidades operacionais no mesmo titulo e horario quando solicitado.
3. Valida limites maximos da agenda por dia, semana e mes.
4. Registra um evento de auditoria com o resultado da geracao.

PONTOS CRITICOS:
- Qualquer erro aqui pode criar grade duplicada ou deixar a equipe com agenda inconsistente.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import ClassSession, SessionStatus


DAILY_SESSION_LIMIT = 12
WEEKLY_SESSION_LIMIT = 70
MONTHLY_SESSION_LIMIT = 150


def get_month_bounds(reference_date):
    month_start = reference_date.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return month_start, month_end


def get_week_bounds(reference_date):
    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


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


def run_class_schedule_create_workflow(*, actor, form):
    title = form.cleaned_data['title']
    coach = form.cleaned_data.get('coach')
    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']
    weekdays = set(form.cleaned_data['weekdays'])
    start_time = form.cleaned_data['start_time']
    duration_minutes = form.cleaned_data['duration_minutes']
    capacity = form.cleaned_data['capacity']
    status = form.cleaned_data['status']
    notes = form.cleaned_data.get('notes') or ''
    skip_existing = bool(form.cleaned_data.get('skip_existing'))
    current_timezone = timezone.get_current_timezone()

    created_sessions = []
    skipped_slots = []
    pending_day_counts = defaultdict(int)
    pending_week_counts = defaultdict(int)
    pending_month_counts = defaultdict(int)
    cursor = start_date

    while cursor <= end_date:
        if cursor.weekday() in weekdays:
            scheduled_at = timezone.make_aware(datetime.combine(cursor, start_time), current_timezone)
            existing_session = ClassSession.objects.filter(title=title, scheduled_at=scheduled_at).first()
            if existing_session is not None and skip_existing:
                skipped_slots.append(scheduled_at)
            else:
                week_key = get_week_bounds(cursor)[0]
                month_key = cursor.replace(day=1)
                ensure_schedule_limits(
                    scheduled_date=cursor,
                    pending_day=pending_day_counts[cursor],
                    pending_week=pending_week_counts[week_key],
                    pending_month=pending_month_counts[month_key],
                )
                created_sessions.append(
                    ClassSession.objects.create(
                        title=title,
                        coach=coach,
                        scheduled_at=scheduled_at,
                        duration_minutes=duration_minutes,
                        capacity=capacity,
                        status=status,
                        notes=notes,
                    )
                )
                pending_day_counts[cursor] += 1
                pending_week_counts[week_key] += 1
                pending_month_counts[month_key] += 1
        cursor += timedelta(days=1)

    log_audit_event(
        actor=actor,
        action='class_schedule_recurring_created',
        target=created_sessions[0] if created_sessions else None,
        description='Agenda recorrente criada pela grade visual de aulas.',
        metadata={
            'title': title,
            'coach_id': coach.id if coach else None,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'weekdays': sorted(weekdays),
            'created_count': len(created_sessions),
            'skipped_count': len(skipped_slots),
        },
    )

    return {
        'created_sessions': created_sessions,
        'skipped_slots': skipped_slots,
    }