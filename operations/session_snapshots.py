"""
ARQUIVO: serializacao compartilhada de aulas para leituras visuais.

POR QUE ELE EXISTE:
- evita duplicar logica de runtime e ocupacao entre dashboard, grade e outras leituras operacionais fora do namespace legado.

O QUE ESTE ARQUIVO FAZ:
1. calcula o estado operacional de uma aula em tempo real.
2. sincroniza aulas que ja deveriam estar finalizadas.
3. serializa uma aula em estrutura pronta para telas de leitura.

PONTOS CRITICOS:
- mudancas aqui afetam dashboard, grade de aulas e qualquer snapshot que reuse essa serializacao.
"""

from django.utils import timezone


COACH_NAME_PREFIXES = {
    'coach',
    'coaches',
    'prof',
    'prof.',
    'professor',
    'professora',
    'teacher',
    'instrutor',
    'instrutora',
}


def _resolve_status_pill(session):
    if session.status in ('scheduled', 'open'):
        return 'class-status-scheduled'
    if session.status == 'canceled':
        return 'class-status-canceled'
    if session.status == 'completed':
        return 'class-status-completed'
    return ''


def build_class_session_runtime_state(session, *, now):
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


def sync_runtime_statuses(sessions, *, now):
    changed_sessions = []
    for session in sessions:
        runtime_state = build_class_session_runtime_state(session, now=now)
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


def _resolve_closed_occupancy_note(runtime_label):
    if runtime_label == 'Em andamento':
        return 'Entradas encerradas enquanto a aula estiver em andamento.'
    if runtime_label == 'Finalizada':
        return 'Entradas encerradas porque a aula ja foi finalizada.'
    return ''


def _resolve_coach_display_name(coach):
    if coach is None:
        return 'Coach'

    full_name = (getattr(coach, 'get_full_name', lambda: '')() or '').strip()
    fallback_name = (getattr(coach, 'username', '') or '').strip()
    raw_name = full_name or fallback_name
    if not raw_name:
        return 'Coach'

    parts = [part for part in raw_name.split() if part]
    if not parts:
        return 'Coach'

    first_part = parts[0].strip(' .').lower()
    if first_part in COACH_NAME_PREFIXES and len(parts) > 1:
        return parts[1]
    return parts[0]


def serialize_class_session(session, *, now):
    occupied_slots = session.occupied_slots
    capacity = session.capacity or 0
    available_slots = max(capacity - occupied_slots, 0)
    occupancy_ratio = (occupied_slots / capacity) if capacity else 0
    runtime_state = build_class_session_runtime_state(session, now=now)
    booking_closed = runtime_state['label'] in ('Em andamento', 'Finalizada')

    if booking_closed:
        occupancy_label = 'Fechado'
        occupancy_pill_class = 'class-occupancy-closed'
        occupancy_fill_class = 'class-occupancy-closed'
        occupancy_percent = 100
        occupancy_note = _resolve_closed_occupancy_note(runtime_state['label'])
    else:
        occupancy_label = 'Lotada' if occupancy_ratio >= 1 else 'Com vagas'
        occupancy_pill_class = _resolve_occupancy_pill(occupancy_ratio)
        occupancy_fill_class = _resolve_occupancy_fill_class(occupancy_ratio)
        occupancy_percent = round(occupancy_ratio * 100)
        occupancy_note = f'{available_slots} vaga(s) restante(s)'

    return {
        'object': session,
        'coach_name': getattr(session.coach, 'get_full_name', lambda: '')() or getattr(session.coach, 'username', '') or 'Coach ainda nao definido',
        'coach_display_name': _resolve_coach_display_name(session.coach),
        'status_label': runtime_state['label'],
        'status_pill_class': runtime_state['pill_class'] or _resolve_status_pill(session),
        'occupied_slots': occupied_slots,
        'available_slots': available_slots,
        'capacity': capacity,
        'occupancy_percent': occupancy_percent,
        'occupancy_label': occupancy_label,
        'occupancy_pill_class': occupancy_pill_class,
        'occupancy_fill_class': occupancy_fill_class,
        'occupancy_note': occupancy_note,
        'booking_closed': booking_closed,
        'starts_at': runtime_state['starts_at'],
        'ends_at': runtime_state['ends_at'],
    }


__all__ = [
    'build_class_session_runtime_state',
    'serialize_class_session',
    'sync_runtime_statuses',
]
