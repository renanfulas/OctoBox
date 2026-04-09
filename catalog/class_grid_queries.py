"""
ARQUIVO: leituras da grade do catalogo.

POR QUE ELE EXISTE:
- centraliza a leitura da agenda e da ocupacao das aulas no app real do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. monta o snapshot da grade de aulas para os proximos dias.
2. resume capacidade, ocupacao e pressao operacional por aula e por dia.

PONTOS CRITICOS:
- mudancas aqui afetam a visao de agenda, ocupacao e planejamento operacional.
"""

from collections import OrderedDict

from django.db.models import Count
from django.utils import timezone

from operations.models import ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses

from catalog.forms import ClassGridFilterForm


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


def _get_month_bounds(reference_month):
	month_start = reference_month.replace(day=1)
	month_end = (month_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
	return month_start, month_end


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

	sync_runtime_statuses(all_sessions, now=current_time)
	if selected_status:
		all_sessions = [session for session in all_sessions if session.status == selected_status]

	grouped_sessions = OrderedDict()
	month_sessions = []
	for session in all_sessions:
		day = timezone.localtime(session.scheduled_at).date()
		serialized_session = serialize_class_session(session, now=current_time)
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
				'summary': f"{len(day_sessions)} aula(s), {total_occupied} reserva(s) e {max(total_capacity - total_occupied, 0)} vaga(s) disponível(eis).",
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
		'selected_month_start': start_date,
		'selected_month_end': end_date,
		'class_metrics': {
			'Aulas previstas': {
				'value': total_sessions,
				'note': f'Total de aulas em {MONTH_LABELS[start_date.month - 1].lower()}.',
			},
			'Dias com agenda': {
				'value': len(grouped_month_days),
				'note': 'Dias com pelo menos uma aula programada.',
			},
			'Reservas confirmadas': {
				'value': total_occupied,
				'note': 'Total de reservas no período.',
			},
			'Aulas lotadas': {
				'value': sum(1 for session in month_sessions if session.occupied_slots >= session.capacity),
				'note': 'Turmas que atingiram a capacidade máxima.',
			},
			'Maior concentração': {
				'value': busiest_day['date'].strftime('%d/%m') if busiest_day else '-',
				'note': f"{len(busiest_day['sessions'])} aula(s) no dia mais cheio." if busiest_day else 'Nenhum dia com aula neste mês.',
			},
			'Capacidade aberta': {
				'value': max(total_capacity - total_occupied, 0),
				'note': 'Vagas disponíveis na grade deste período.',
			},
		},
	}


__all__ = ['build_class_grid_snapshot']
