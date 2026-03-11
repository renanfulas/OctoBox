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
    if session.status == ClassSession._meta.get_field('status').choices[0][0]:
        return ''
    if session.status == 'open':
        return 'info'
    if session.status == 'canceled':
        return 'warning'
    return ''


def _resolve_occupancy_pill(occupancy_ratio):
    if occupancy_ratio >= 1:
        return 'warning'
    if occupancy_ratio >= 0.75:
        return 'info'
    return ''


def _get_month_bounds(reference_month):
    month_start = reference_month.replace(day=1)
    month_end = (month_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
    return month_start, month_end


def _serialize_session(session):
    occupied_slots = session.occupied_slots
    capacity = session.capacity or 0
    available_slots = max(capacity - occupied_slots, 0)
    occupancy_ratio = (occupied_slots / capacity) if capacity else 0
    starts_at = timezone.localtime(session.scheduled_at)
    return {
        'object': session,
        'coach_name': getattr(session.coach, 'get_full_name', lambda: '')() or getattr(session.coach, 'username', '') or 'Coach nao definido',
        'status_label': session.get_status_display(),
        'status_pill_class': _resolve_status_pill(session),
        'occupied_slots': occupied_slots,
        'available_slots': available_slots,
        'capacity': capacity,
        'occupancy_percent': round(occupancy_ratio * 100),
        'occupancy_label': 'Lotada' if occupancy_ratio >= 1 else 'Quase cheia' if occupancy_ratio >= 0.75 else 'Com vagas',
        'occupancy_pill_class': _resolve_occupancy_pill(occupancy_ratio),
        'starts_at': starts_at,
        'ends_at': starts_at + timezone.timedelta(minutes=session.duration_minutes),
    }


def build_class_grid_snapshot(today, params=None):
    filter_form = ClassGridFilterForm(params or None)
    filter_form.is_valid()
    cleaned_data = filter_form.cleaned_data if filter_form.is_valid() else {}
    reference_month = cleaned_data.get('reference_month') or today.replace(day=1)
    selected_coach = cleaned_data.get('coach')
    selected_status = cleaned_data.get('status')

    start_date, end_date = _get_month_bounds(reference_month)
    sessions = list(
        ClassSession.objects.filter(scheduled_at__date__gte=start_date, scheduled_at__date__lte=end_date)
        .filter(coach=selected_coach) if selected_coach else ClassSession.objects.filter(scheduled_at__date__gte=start_date, scheduled_at__date__lte=end_date)
    )
    if selected_status:
        sessions_queryset = ClassSession.objects.filter(scheduled_at__date__gte=start_date, scheduled_at__date__lte=end_date, status=selected_status)
        if selected_coach:
            sessions_queryset = sessions_queryset.filter(coach=selected_coach)
    else:
        sessions_queryset = ClassSession.objects.filter(scheduled_at__date__gte=start_date, scheduled_at__date__lte=end_date)
        if selected_coach:
            sessions_queryset = sessions_queryset.filter(coach=selected_coach)

    sessions = list(
        sessions_queryset
        .select_related('coach')
        .annotate(occupied_slots=Count('attendances'))
        .order_by('scheduled_at')
    )

    grouped_sessions = OrderedDict()
    for session in sessions:
        day = timezone.localtime(session.scheduled_at).date()
        grouped_sessions.setdefault(day, []).append(_serialize_session(session))

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

    calendar_start = start_date - timezone.timedelta(days=start_date.weekday())
    calendar_end = end_date + timezone.timedelta(days=(6 - end_date.weekday()))
    weekly_calendar = []
    cursor = calendar_start
    while cursor <= calendar_end:
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
    for week in weekly_calendar:
        month_days = []
        for day in week['days']:
            visible_sessions = day['sessions'][:3]
            month_days.append(
                {
                    'date': day['date'],
                    'is_today': day['is_today'],
                    'is_in_month': start_date <= day['date'] <= end_date,
                    'visible_sessions': visible_sessions,
                    'remaining_sessions': max(len(day['sessions']) - len(visible_sessions), 0),
                    'session_count': len(day['sessions']),
                }
            )
        monthly_calendar.append(month_days)

    total_sessions = len(sessions)
    total_capacity = sum(session.capacity for session in sessions)
    total_occupied = sum(session.occupied_slots for session in sessions)
    busiest_day = max(grouped_days, key=lambda item: len(item['sessions']), default=None)

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
                'note': f'Recorte de {MONTH_LABELS[start_date.month - 1].lower()} filtrado na agenda.',
            },
            'Dias com agenda': {
                'value': len(grouped_days),
                'note': 'Dias com pelo menos uma aula cadastrada.',
            },
            'Reservas confirmadas': {
                'value': total_occupied,
                'note': 'Soma das reservas registradas na janela.',
            },
            'Aulas lotadas': {
                'value': sum(1 for session in sessions if session.occupied_slots >= session.capacity),
                'note': 'Turmas que ja bateram a capacidade maxima.',
            },
            'Maior concentracao': {
                'value': busiest_day['date'].strftime('%d/%m') if busiest_day else '-',
                'note': f"{len(busiest_day['sessions'])} aula(s) no dia mais carregado." if busiest_day else 'Nenhum dia com agenda cadastrada.',
            },
            'Capacidade aberta': {
                'value': max(total_capacity - total_occupied, 0),
                'note': 'Vagas ainda disponiveis na grade atual.',
            },
        },
    }