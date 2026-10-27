"""Fingerprints canônicos para confirmar apenas o estado visto na prévia."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.core import signing
from django.db import connection
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.models import ClassSession, WorkoutProgram, WorkoutTemplate
from operations.workout_approval_policy import lock_workout_approval_policy, resolve_workout_approval_policy
from shared_support.cascade.ownership import resolve_actor_box_id
from student_app.models import SessionWorkout


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def lock_workout_policy_for_actor(actor):
    box_id = resolve_actor_box_id(actor)
    if box_id is not None:
        lock_workout_approval_policy(box_id=box_id)


def _template_content(template, *, lock=False):
    blocks = []
    block_query = template.blocks.order_by('id')
    if lock:
        block_query = block_query.select_for_update()
    for block in block_query:
        movements = []
        movement_query = block.movements.order_by('id')
        if lock:
            movement_query = movement_query.select_for_update()
        for movement in movement_query:
            movements.append({field.attname: getattr(movement, field.attname) for field in movement._meta.concrete_fields if field.name not in {'created_at', 'updated_at'}})
        blocks.append({
            'fields': {field.attname: getattr(block, field.attname) for field in block._meta.concrete_fields if field.name not in {'created_at', 'updated_at'}},
            'movements': movements,
        })
    return {
        'id': template.pk, 'name': template.name, 'description': template.description,
        'is_active': template.is_active, 'is_trusted': template.is_trusted,
        'archived_at': template.archived_at, 'created_by_id': template.created_by_id,
        'blocks': blocks,
    }


def daily_program_snapshot(*, actor, target_date, template_id, workout_program_id, mode, lock=False):
    role = get_user_role(actor)
    if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        raise PermissionDenied('Sem permissão para aplicar WODs.')
    if mode not in {'replace_empty', 'overwrite'}:
        raise ValidationError('Escolha o modo de aplicação.')
    template_query = WorkoutTemplate.objects
    if lock:
        lock_workout_policy_for_actor(actor)
        template_query = template_query.select_for_update()
    template = template_query.filter(pk=template_id, is_active=True, archived_at__isnull=True).first()
    if template is None:
        raise ValidationError('Template não encontrado ou arquivado.')
    if role.slug == ROLE_COACH and template.created_by_id != actor.pk:
        raise PermissionDenied('Use um template criado por você.')
    program_query = WorkoutProgram.objects.select_for_update() if lock else WorkoutProgram.objects
    program = program_query.filter(pk=workout_program_id, is_active=True).first()
    if program is None:
        raise ValidationError('Programa não encontrado ou inativo.')

    start = timezone.make_aware(datetime.combine(target_date, time.min))
    sessions_query = ClassSession.objects.filter(
        scheduled_at__gte=start, scheduled_at__lt=start + timedelta(days=1),
        workout_program_id=program.pk,
    ).order_by('id')
    if role.slug == ROLE_COACH:
        sessions_query = sessions_query.filter(coach=actor)
    if lock:
        sessions_query = sessions_query.select_for_update()
    sessions = list(sessions_query)
    workout_query = SessionWorkout.objects.filter(session_id__in=[session.pk for session in sessions]).order_by('session_id')
    if lock:
        workout_query = workout_query.select_for_update()
    workouts = {workout.session_id: workout for workout in workout_query}
    entries = []
    for session in sessions:
        workout = workouts.get(session.pk)
        if session.status == 'completed':
            status = 'skipped_completed'
        elif session.status == 'canceled':
            status = 'skipped_canceled'
        elif workout and (mode == 'replace_empty' or workout.status != 'draft'):
            status = 'preserved'
        else:
            status = 'ready'
        entries.append({
            'session_id': session.pk, 'title': session.title,
            'scheduled_at': session.scheduled_at.isoformat(),
            'coach_id': session.coach_id, 'program_id': session.workout_program_id,
            'class_type': session.class_type, 'session_status': session.status,
            'workout_id': workout.pk if workout else None,
            'workout_version': workout.version if workout else None,
            'workout_status': workout.status if workout else None,
            'status': status,
        })
    snapshot = {
        'contract': 'daily-program-v1', 'actor_id': actor.pk, 'role': role.slug,
        'date': target_date.isoformat(), 'program_id': program.pk, 'program_name': program.name,
        'program_active': program.is_active, 'mode': mode,
        'template': _template_content(template, lock=lock),
        'policy_by_session': {str(session.pk): resolve_workout_approval_policy(actor=actor, session=session) for session in sessions},
        'entries': entries,
    }
    return json.loads(json.dumps(snapshot, ensure_ascii=False, default=str)), template, sessions, workouts


__all__ = ['daily_program_snapshot', 'fingerprint', 'lock_workout_policy_for_actor']


_WEEKLY_TOKEN_SALT = 'wod-weekly-projection-v1'


def _model_content(instance):
    return {field.attname: getattr(instance, field.attname) for field in instance._meta.concrete_fields if field.name not in {'created_at', 'updated_at'}}


def projection_contract_fingerprint(*, weekly_plan, target_week_start, class_types, actor, preview):
    start = timezone.make_aware(datetime.combine(target_week_start, time.min))
    sessions = ClassSession.objects.filter(scheduled_at__gte=start, scheduled_at__lt=start + timedelta(days=7))
    if weekly_plan.workout_program_id:
        sessions = sessions.filter(workout_program_id=weekly_plan.workout_program_id)
    else:
        sessions = sessions.filter(class_type__in=class_types)
    sessions = list(sessions.order_by('id'))
    workouts = {item.session_id: item for item in SessionWorkout.objects.filter(session_id__in=[session.pk for session in sessions])}
    destinations = [{
        'session': _model_content(session),
        'workout': _model_content(workouts[session.pk]) if session.pk in workouts else None,
        'policy': resolve_workout_approval_policy(actor=actor, session=session),
    } for session in sessions]
    relational_days = []
    for day in weekly_plan.days.order_by('weekday', 'id'):
        blocks = []
        for block in day.blocks.order_by('sort_order', 'id'):
            blocks.append({'block': _model_content(block), 'movements': [
                _model_content(movement) for movement in block.movements.order_by('sort_order', 'id')
            ]})
        relational_days.append({'day': _model_content(day), 'blocks': blocks})
    payload = {
        'contract': 'weekly-projection-v1', 'schema_name': connection.schema_name, 'actor_id': actor.pk,
        'plan_id': weekly_plan.pk, 'revision': weekly_plan.revision,
        'status': weekly_plan.status, 'source_text': weekly_plan.source_text,
        'parsed_payload': weekly_plan.parsed_payload, 'week_start': weekly_plan.week_start,
        'label': weekly_plan.label, 'workout_program_id': weekly_plan.workout_program_id,
        'program': _model_content(weekly_plan.workout_program) if weekly_plan.workout_program_id else None,
        'relational_days': relational_days,
        'target_week_start': target_week_start, 'class_types': sorted(set(class_types)),
        'destinations': destinations,
        'projection_entries': [
            {key: value for key, value in entry.items() if key not in {'status_label', 'class_type_label'}}
            for entry in preview['entries']
        ],
    }
    return fingerprint(payload)


def issue_projection_token(*, weekly_plan, target_week_start, class_types, actor, preview, intent_id):
    key = str(UUID(str(intent_id)))
    digest = projection_contract_fingerprint(
        weekly_plan=weekly_plan, target_week_start=target_week_start,
        class_types=class_types, actor=actor, preview=preview,
    )
    return signing.dumps({
        'schema_name': connection.schema_name,
        'actor_id': actor.pk, 'plan_id': weekly_plan.pk, 'target_week_start': target_week_start.isoformat(),
        'class_types': sorted(set(class_types)), 'intent_id': key, 'fingerprint': digest,
    }, salt=_WEEKLY_TOKEN_SALT)


def read_projection_token(token, *, allow_expired=False):
    claim = signing.loads(token, salt=_WEEKLY_TOKEN_SALT, max_age=None if allow_expired else 1800)
    # IDs de planos/aulas podem coincidir entre schemas; a assinatura global
    # não basta para autorizar uma prévia depois de trocar o box ativo.
    schema_name = connection.schema_name
    if (
        not isinstance(claim, dict) or not schema_name or schema_name == get_public_schema_name()
        or claim.get('schema_name') != schema_name
    ):
        raise signing.BadSignature('A prévia não pertence ao box ativo.')
    return claim


__all__ += ['projection_contract_fingerprint', 'issue_projection_token', 'read_projection_token']
