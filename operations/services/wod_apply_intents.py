"""Confirmação diária atômica e idempotente por programa de treino."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.services.wod_day_apply_executor import apply_template_to_locked_sessions
from operations.services.wod_preview_contracts import daily_program_snapshot, fingerprint
from student_app.models import WodApplyIntent


class WodApplyConflict(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def prepare_program_apply(*, actor, target_date, template_id, workout_program_id, mode):
    snapshot, _template, _sessions, _workouts = daily_program_snapshot(
        actor=actor, target_date=target_date, template_id=template_id,
        workout_program_id=workout_program_id, mode=mode,
    )
    intent = WodApplyIntent.objects.create(
        author=actor, target_date=target_date, workout_program_id=workout_program_id,
        template_id=template_id, mode=mode, fingerprint=fingerprint(snapshot),
        preview_snapshot=snapshot, expires_at=timezone.now() + timedelta(minutes=30),
    )
    entries = [{
        'session_id': entry['session_id'], 'title': entry['title'],
        'scheduled_at': timezone.localtime(datetime.fromisoformat(entry['scheduled_at'])).strftime('%H:%M'),
        'program': snapshot['program_name'], 'status': entry['status'],
        'reason': {
            'ready': 'Receberá o template como rascunho.',
            'preserved': 'WOD existente preservado.',
            'skipped_completed': 'Aula concluída preservada.',
            'skipped_canceled': 'Aula cancelada preservada.',
        }[entry['status']],
    } for entry in snapshot['entries']]
    return {
        'ok': True, 'scope': 'workout_program', 'intent_id': str(intent.pk),
        'fingerprint': intent.fingerprint, 'expires_at': intent.expires_at.isoformat(),
        'template': snapshot['template']['name'], 'date': snapshot['date'],
        'program': snapshot['program_name'], 'entries': entries,
        'ready_count': sum(entry['status'] == 'ready' for entry in entries),
        'preserved_count': sum(entry['status'] == 'preserved' for entry in entries),
        'completed_count': sum(entry['status'] == 'skipped_completed' for entry in entries),
        'mixed_programs': False,
    }


@transaction.atomic
def confirm_program_apply(*, actor, intent_id: UUID, request_fingerprint: str):
    role = get_user_role(actor)
    if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        raise PermissionDenied('Sem permissão para aplicar WODs.')
    intent = WodApplyIntent.objects.select_for_update().filter(pk=intent_id, author=actor).first()
    if intent is None:
        raise WodApplyConflict('not_found', 'Prévia não encontrada.')
    if request_fingerprint != intent.fingerprint:
        raise WodApplyConflict('idempotency_key_reused', 'Esta intenção pertence a outra prévia.')
    if intent.state == WodApplyIntent.State.CONFIRMED:
        return {**intent.response_payload, 'idempotent_replay': True}
    if timezone.now() > intent.expires_at:
        raise WodApplyConflict('stale_preview', 'A prévia expirou. Confira as aulas novamente.')
    try:
        snapshot, template, sessions, workouts = daily_program_snapshot(
            actor=actor, target_date=intent.target_date, template_id=intent.template_id,
            workout_program_id=intent.workout_program_id, mode=intent.mode, lock=True,
        )
    except ValidationError as error:
        raise WodApplyConflict('stale_preview', error.messages[0]) from error
    if fingerprint(snapshot) != intent.fingerprint:
        raise WodApplyConflict('stale_preview', 'Aulas, WODs, template ou política mudaram. Confira a prévia novamente.')
    response_holder = {}

    def mark_undo_unavailable():
        response = response_holder.get('response')
        if response is None:
            return
        response['undo_token'] = ''
        response['undo_expires_at'] = None
        response['undo_unavailable'] = True
        WodApplyIntent.objects.filter(pk=intent.pk, state=WodApplyIntent.State.CONFIRMED).update(
            response_payload=response,
        )

    result = apply_template_to_locked_sessions(
        actor=actor, template=template, sessions=sessions, workouts=workouts,
        mode=intent.mode, skip_completed=True, defer_undo_cache=True,
        on_undo_unavailable=mark_undo_unavailable,
    )
    response = {
        'ok': True, 'applied_count': result.applied_count,
        'skipped_count': result.skipped_count, 'undo_token': result.undo_token,
        'undo_expires_at': (timezone.now() + timedelta(seconds=60)).isoformat() if result.undo_token else None,
        'skipped_reasons': result.skipped_reasons,
        'applied_session_ids': result.applied_session_ids,
        'skipped_completed': sum(reason.get('code') == 'skipped_completed' for reason in result.skipped_reasons),
        'intent_id': str(intent.pk), 'fingerprint': intent.fingerprint,
        'idempotent_replay': False,
    }
    intent.response_payload = response
    intent.state = WodApplyIntent.State.CONFIRMED
    intent.confirmed_at = timezone.now()
    intent.save(update_fields=['response_payload', 'state', 'confirmed_at', 'updated_at'])
    response_holder['response'] = response
    return response


__all__ = ['WodApplyConflict', 'prepare_program_apply', 'confirm_program_apply']
