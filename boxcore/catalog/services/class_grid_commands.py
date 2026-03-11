"""
ARQUIVO: comandos operacionais da grade de aulas.

POR QUE ELE EXISTE:
- organiza cada mutacao rapida da grade em comandos pequenos com regras explicitas por acao.

O QUE ESTE ARQUIVO FAZ:
1. executa update e delete de aula.
2. consulta a policy da aula antes de mutar o registro.
3. devolve resultado padronizado para a view exibir mensagem sem conhecer detalhes internos.

PONTOS CRITICOS:
- comandos alteram dados reais da agenda e precisam manter auditoria, policy e limites coerentes.
"""

from dataclasses import dataclass, field

from boxcore.auditing import log_audit_event
from boxcore.models import SessionStatus

from . import class_grid_messages as grid_messages
from .class_grid_policy import build_class_grid_session_policy
from .class_schedule_workflows import ensure_schedule_limits


@dataclass(frozen=True)
class ClassGridCommandResult:
    message: str
    payload: dict = field(default_factory=dict)


def run_class_session_update_command(*, actor, session, form):
    policy = build_class_grid_session_policy(session)
    scheduled_at = form.cleaned_data['scheduled_at']
    target_date = scheduled_at.date()
    new_status = form.cleaned_data['status']

    policy.validate_quick_edit_status(new_status)
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
    return ClassGridCommandResult(
        message=grid_messages.session_updated_success(session.title),
        payload={'session': session},
    )


def run_class_session_delete_command(*, actor, session):
    policy = build_class_grid_session_policy(session)
    policy.ensure_can_delete()

    session_snapshot = {
        'id': session.id,
        'title': session.title,
        'scheduled_at': session.scheduled_at.isoformat(),
        'status': session.status,
    }
    log_audit_event(
        actor=actor,
        action='class_session_quick_deleted',
        target=session,
        description='Aula excluida pela grade visual.',
        metadata=session_snapshot,
    )
    session.delete()
    return ClassGridCommandResult(
        message=grid_messages.session_deleted_success(session_snapshot['title']),
        payload=session_snapshot,
    )


CLASS_GRID_ACTION_COMMANDS = {
    'delete-session': run_class_session_delete_command,
}