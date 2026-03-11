"""
ARQUIVO: actions rapidas da grade de aulas.

POR QUE ELE EXISTE:
- Tira da view as mutacoes pontuais de editar, cancelar e duplicar aulas da agenda visual.

O QUE ESTE ARQUIVO FAZ:
1. Atualiza os dados operacionais de uma aula.
2. Cancela uma aula existente sem excluir historico.
3. Duplica uma aula para a semana seguinte respeitando os limites da agenda.

PONTOS CRITICOS:
- Essas actions alteram a agenda real do box e precisam respeitar limites e auditoria.
"""

from datetime import timedelta

from boxcore.auditing import log_audit_event
from boxcore.models import ClassSession, SessionStatus

from .class_schedule_workflows import ensure_schedule_limits


def handle_class_session_update_action(*, actor, session, form):
    scheduled_at = form.cleaned_data['scheduled_at']
    target_date = scheduled_at.date()
    new_status = form.cleaned_data['status']
    if new_status != SessionStatus.CANCELED:
        ensure_schedule_limits(
            scheduled_date=target_date,
            exclude_session_ids=[session.id],
        )

    session.title = form.cleaned_data['title']
    session.coach = form.cleaned_data.get('coach')
    session.scheduled_at = scheduled_at
    session.duration_minutes = form.cleaned_data['duration_minutes']
    session.capacity = form.cleaned_data['capacity']
    session.status = new_status
    session.notes = form.cleaned_data.get('notes') or ''
    session.save()

    log_audit_event(
        actor=actor,
        action='class_session_quick_updated',
        target=session,
        description='Aula ajustada pela grade visual.',
        metadata={'status': session.status, 'scheduled_at': session.scheduled_at.isoformat()},
    )
    return session


def handle_class_session_cancel_action(*, actor, session):
    session.status = SessionStatus.CANCELED
    session.save(update_fields=['status'])
    log_audit_event(
        actor=actor,
        action='class_session_quick_canceled',
        target=session,
        description='Aula cancelada pela grade visual.',
        metadata={'scheduled_at': session.scheduled_at.isoformat()},
    )
    return session


def handle_class_session_duplicate_action(*, actor, session):
    duplicated_start = session.scheduled_at + timedelta(days=7)
    target_date = duplicated_start.date()
    ensure_schedule_limits(scheduled_date=target_date)
    if ClassSession.objects.filter(title=session.title, scheduled_at=duplicated_start).exists():
        raise ValueError('Ja existe uma aula com esse mesmo nome e horario na semana seguinte.')

    duplicated_session = ClassSession.objects.create(
        title=session.title,
        coach=session.coach,
        scheduled_at=duplicated_start,
        duration_minutes=session.duration_minutes,
        capacity=session.capacity,
        status=session.status,
        notes=session.notes,
    )
    log_audit_event(
        actor=actor,
        action='class_session_quick_duplicated',
        target=duplicated_session,
        description='Aula duplicada para a semana seguinte pela grade visual.',
        metadata={'source_session_id': session.id},
    )
    return duplicated_session