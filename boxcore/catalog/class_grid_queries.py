"""
ARQUIVO: queries da grade de aulas do catalogo.

POR QUE ELE EXISTE:
- Centraliza a leitura da agenda e da ocupacao das aulas.

O QUE ESTE ARQUIVO FAZ:
1. Monta o snapshot da grade de aulas para os proximos dias.
2. Resume capacidade, ocupacao e pressao operacional por aula e por dia.

PONTOS CRITICOS:
- Mudancas aqui afetam a visao de agenda, ocupacao e planejamento operacional.
"""

from collections import OrderedDict

from django.db.models import Count
from django.utils import timezone

from boxcore.models import ClassSession

from .forms import ClassGridFilterForm


WEEKDAY_LABELS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom')
MONTH_LABELS = (
    'Janeiro',
    'Fevereiro',
    'Marco',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro',
)


def _resolve_status_pill(session):
    if session.status in ('scheduled', 'open'):
        return 'class-status-scheduled'
    if session.status == 'canceled':
        return 'class-status-canceled'
    if session.status == 'completed':
        return 'class-status-completed'
    return ''


def _build_session_runtime_state(session, *, now):
    starts_at = timezone.localtime(session.scheduled_at)
    ends_at = starts_at + timezone.timedelta(minutes=session.duration_minutes)

    if session.status == 'canceled':
        return {
            'label': 'Cancelada',
            'pill_class': 'class-status-canceled',
            'starts_at': starts_at,
            'ends_at': ends_at,
            'should_mark_completed': False,
        }

    if starts_at <= now <= ends_at:
        return {
            'label': 'Em andamento',
            'pill_class': 'class-status-in-progress',
            'starts_at': starts_at,
            'ends_at': ends_at,
            'should_mark_completed': False,
        }

    if now > ends_at:
        return {
            'label': 'Finalizada',
            'pill_class': 'class-status-completed',
            'starts_at': starts_at,
            'ends_at': ends_at,
            'should_mark_completed': session.status != 'completed',
        }

    if session.status == 'open':
        runtime_label = 'Agendada'
        runtime_pill_class = 'class-status-scheduled'
    elif session.status == 'completed':
        runtime_label = 'Finalizada'
        runtime_pill_class = 'class-status-completed'
    else:
        runtime_label = 'Agendada'
        runtime_pill_class = 'class-status-scheduled'

    return {
        'label': runtime_label,
        'pill_class': runtime_pill_class,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'should_mark_completed': False,
    }


def _sync_runtime_statuses(sessions, *, now):
    changed_sessions = []
    for session in sessions:
        runtime_state = _build_session_runtime_state(session, now=now)
        if runtime_state['should_mark_completed']:
            session.status = 'completed'
            session.save(update_fields=['status'])
            changed_sessions.append(session.pk)
    return changed_sessions


def _resolve_occupancy_pill(occupancy_ratio):
    if occupancy_ratio >= 0.9:
        return 'class-occupancy-critical'
    if occupancy_ratio >= 0.7:
        return 'class-occupancy-high'
    if occupancy_ratio >= 0.5:
        return 'class-occupancy-medium'
    return 'class-occupancy-available'


def _resolve_occupancy_fill_class(occupancy_ratio):
    if occupancy_ratio >= 0.9:
        return 'class-occupancy-critical'
    if occupancy_ratio >= 0.7:
        return 'class-occupancy-high'
    if occupancy_ratio >= 0.5:
        return 'class-occupancy-medium'
    return 'class-occupancy-available'


def _get_month_bounds(reference_month):
    month_start = reference_month.replace(day=1)
    month_end = (month_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
    return month_start, month_end


def _serialize_session(session, *, now):
    occupied_slots = session.occupied_slots
    capacity = session.capacity or 0
    available_slots = max(capacity - occupied_slots, 0)
    occupancy_ratio = (occupied_slots / capacity) if capacity else 0
    runtime_state = _build_session_runtime_state(session, now=now)
    booking_closed = runtime_state['label'] == 'Em andamento'
    occupancy_label = 'Lotada' if occupancy_ratio >= 1 else 'Com vagas'
    occupancy_pill_class = _resolve_occupancy_pill(occupancy_ratio)
    occupancy_fill_class = _resolve_occupancy_fill_class(occupancy_ratio)

    if booking_closed:
        occupancy_note = 'Entradas encerradas enquanto a aula estiver em andamento.'
    else:
        occupancy_note = f'{available_slots} vaga(s) restante(s)'

    return {
        'object': session,
        'coach_name': getattr(session.coach, 'get_full_name', lambda: '')() or getattr(session.coach, 'username', '') or 'Coach ainda nao definido',
        'status_label': runtime_state['label'],
        'status_pill_class': runtime_state['pill_class'] or _resolve_status_pill(session),
        'occupied_slots': occupied_slots,
        'available_slots': available_slots,
        'capacity': capacity,
        'occupancy_percent': round(occupancy_ratio * 100),
        'occupancy_label': occupancy_label,
        'occupancy_pill_class': occupancy_pill_class,
        'occupancy_fill_class': occupancy_fill_class,
        'occupancy_note': occupancy_note,
        'booking_closed': booking_closed,
        'starts_at': runtime_state['starts_at'],
        'ends_at': runtime_state['ends_at'],
    }


def build_class_grid_snapshot(today, params=None):
    filter_form = ClassGridFilterForm(params or None)
    filter_form.is_valid()
    cleaned_data = filter_form.cleaned_data if filter_form.is_valid() else {}
    reference_month = cleaned_data.get('reference_month') or today.replace(day=1)
    selected_coach = cleaned_data.get('coach')
    selected_status = cleaned_data.get('status')
    current_time = timezone.localtime()

    start_date, end_date = _get_month_bounds(reference_month)
    weekly_start_date = today - timezone.timedelta(days=today.weekday())
    weekly_end_date = weekly_start_date + timezone.timedelta(days=13)
    query_start_date = min(start_date, weekly_start_date)
    query_end_date = max(end_date, weekly_end_date)

    sessions_queryset = ClassSession.objects.filter(
        scheduled_at__date__gte=query_start_date,
        scheduled_at__date__lte=query_end_date,
    )
    if selected_coach:
        sessions_queryset = sessions_queryset.filter(coach=selected_coach)

    all_sessions = list(
        sessions_queryset
        .select_related('coach')
        .annotate(occupied_slots=Count('attendances'))
        .order_by('scheduled_at')
    )

    _sync_runtime_statuses(all_sessions, now=current_time)
    if selected_status:
        all_sessions = [session for session in all_sessions if session.status == selected_status]

    grouped_sessions = OrderedDict()
    month_sessions = []
    for session in all_sessions:
        day = timezone.localtime(session.scheduled_at).date()
        serialized_session = _serialize_session(session, now=current_time)
        grouped_sessions.setdefault(day, []).append(serialized_session)
        if start_date <= day <= end_date:
            month_sessions.append(session)

    grouped_days = []
    for day, day_sessions in grouped_sessions.items():
        total_capacity = sum(item['capacity'] for item in day_sessions)
        total_occupied = sum(item['occupied_slots'] for item in day_sessions)
        grouped_days.append(
            {
                'date': day,
                'sessions': day_sessions,
                'summary': f"{len(day_sessions)} aula(s), {total_occupied} reserva(s) e {max(total_capacity - total_occupied, 0)} vaga(s) restante(s).",
            }
        )

    today_schedule = next((item for item in grouped_days if item['date'] == today), None)

    weekly_calendar = []
    cursor = weekly_start_date
    while cursor <= weekly_end_date:
        week_days = []
        for _ in range(7):
            sessions_for_day = list(grouped_sessions.get(cursor, []))
            week_days.append(
                {
                    'date': cursor,
                    'weekday_label': WEEKDAY_LABELS[cursor.weekday()],
                    'is_today': cursor == today,
                    'is_in_window': start_date <= cursor <= end_date,
                    'sessions': sessions_for_day,
                }
            )
            cursor += timezone.timedelta(days=1)
        weekly_calendar.append(
            {
                'label': f"Semana de {week_days[0]['date'].strftime('%d/%m')} a {week_days[-1]['date'].strftime('%d/%m')}",
                'days': week_days,
            }
        )

    monthly_calendar = []
    monthly_cursor = start_date - timezone.timedelta(days=start_date.weekday())
    monthly_calendar_end = end_date + timezone.timedelta(days=(6 - end_date.weekday()))
    while monthly_cursor <= monthly_calendar_end:
        month_days = []
        for _ in range(7):
            sessions_for_day = list(grouped_sessions.get(monthly_cursor, []))
            visible_sessions = sessions_for_day[:3]
            month_days.append(
                {
                    'date': monthly_cursor,
                    'is_today': monthly_cursor == today,
                    'is_in_month': start_date <= monthly_cursor <= end_date,
                    'visible_sessions': visible_sessions,
                    'remaining_sessions': max(len(sessions_for_day) - len(visible_sessions), 0),
                    'session_count': len(sessions_for_day),
                }
            )
            monthly_cursor += timezone.timedelta(days=1)
        monthly_calendar.append(month_days)

    grouped_month_days = [item for item in grouped_days if start_date <= item['date'] <= end_date]
    total_sessions = len(month_sessions)
    total_capacity = sum(session.capacity for session in month_sessions)
    total_occupied = sum(session.occupied_slots for session in month_sessions)
    busiest_day = max(grouped_month_days, key=lambda item: len(item['sessions']), default=None)

    return {
        'filter_form': filter_form,
        'grouped_sessions': grouped_days,
        'today_schedule': today_schedule,
        'weekly_calendar': weekly_calendar,
        'monthly_calendar': monthly_calendar,
        'selected_month_label': f"{MONTH_LABELS[start_date.month - 1]} de {start_date.year}",
        'class_metrics': {
            'Aulas previstas': {
                'value': total_sessions,
                'note': f'Recorte de {MONTH_LABELS[start_date.month - 1].lower()} aplicado na agenda.',
            },
            'Dias com agenda': {
                'value': len(grouped_month_days),
                'note': 'Dias com pelo menos uma aula cadastrada.',
            },
            'Reservas confirmadas': {
                'value': total_occupied,
                'note': 'Soma das reservas registradas neste recorte.',
            },
            'Aulas lotadas': {
                'value': sum(1 for session in month_sessions if session.occupied_slots >= session.capacity),
                'note': 'Turmas que ja atingiram a capacidade maxima.',
            },
            'Maior concentracao': {
                'value': busiest_day['date'].strftime('%d/%m') if busiest_day else '-',
                'note': f"{len(busiest_day['sessions'])} aula(s) no dia mais carregado." if busiest_day else 'Nenhum dia com agenda cadastrada.',
            },
            'Capacidade aberta': {
                'value': max(total_capacity - total_occupied, 0),
                'note': 'Vagas ainda disponiveis na grade deste recorte.',
            },
        },
    }