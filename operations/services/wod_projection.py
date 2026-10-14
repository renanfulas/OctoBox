"""
ARQUIVO: projeção de plano semanal para WODs draft por aula.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from operations.models import ClassSession, ClassType, SessionStatus
from student_app.models import (
    PlanBlockKind,
    ReplicationBatch,
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    WorkoutLoadType,
)
from operations.workout_support import route_workout_submission


CLASS_TYPE_COMPATIBILITY = {
    ClassType.CROSS: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.STRENGTH,
        PlanBlockKind.SKILL,
        PlanBlockKind.METCON,
        PlanBlockKind.COOLDOWN,
        PlanBlockKind.MOBILITY,
        PlanBlockKind.CUSTOM,
    },
    ClassType.MOBILITY: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.COOLDOWN,
        PlanBlockKind.MOBILITY,
    },
    ClassType.OLY: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.SKILL,
        PlanBlockKind.COOLDOWN,
    },
    ClassType.STRENGTH: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.STRENGTH,
        PlanBlockKind.SKILL,
        PlanBlockKind.COOLDOWN,
    },
    ClassType.OPEN_GYM: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.STRENGTH,
        PlanBlockKind.SKILL,
        PlanBlockKind.METCON,
        PlanBlockKind.COOLDOWN,
        PlanBlockKind.MOBILITY,
        PlanBlockKind.CUSTOM,
    },
    ClassType.OTHER: {
        PlanBlockKind.WARMUP,
        PlanBlockKind.STRENGTH,
        PlanBlockKind.SKILL,
        PlanBlockKind.METCON,
        PlanBlockKind.COOLDOWN,
        PlanBlockKind.MOBILITY,
        PlanBlockKind.CUSTOM,
    },
}


_WEEKDAY_TITLES = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')


def _session_workout_title(*, weekly_plan, session):
    weekday = _WEEKDAY_TITLES[timezone.localtime(session.scheduled_at).weekday()]
    label = (weekly_plan.label or '').strip()
    return (f'{weekday} · {label}' if label else f'WOD de {weekday}')[:140]


def _expand_projection_class_types(class_types):
    # Legacy fallback only. A CrossFit plan must never implicitly include OTHER.
    return list(class_types or [ClassType.CROSS])


def _session_track_filter(sessions, weekly_plan, class_types):
    program_id = getattr(weekly_plan, 'workout_program_id', None)
    if program_id:
        return sessions.filter(workout_program_id=program_id)
    return sessions.filter(class_type__in=_expand_projection_class_types(class_types))


def _week_range(week_start):
    start = datetime.combine(week_start, time.min)
    end = start + timedelta(days=7)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(start, tz), timezone.make_aware(end, tz)


def _extract_plan_days(weekly_plan):
    days = {}
    if weekly_plan.days.exists():
        for day in weekly_plan.days.prefetch_related('blocks__movements').all():
            days[day.weekday] = day
        return days
    for day in weekly_plan.parsed_payload.get('days', []):
        days[day['weekday']] = day
    return days


def _compatible_kinds_for(class_type):
    return CLASS_TYPE_COMPATIBILITY.get(class_type or ClassType.OTHER, CLASS_TYPE_COMPATIBILITY[ClassType.OTHER])


def _compatible_kinds_for_session(session):
    program = getattr(session, 'workout_program', None)
    if program and program.allowed_block_kinds:
        return set(program.allowed_block_kinds)
    return _compatible_kinds_for(session.class_type)


def _normalize_plan_blocks(day_plan):
    if isinstance(day_plan, dict):
        return day_plan.get('blocks', [])
    return list(day_plan.blocks.prefetch_related('movements').all())


def _block_kind(block):
    return block['kind'] if isinstance(block, dict) else block.kind


def _block_title(block):
    return block.get('title') if isinstance(block, dict) else block.title


def _block_notes(block):
    return block.get('notes') if isinstance(block, dict) else block.notes


def _block_value(block, name, default=None):
    return block.get(name, default) if isinstance(block, dict) else getattr(block, name, default)


def _block_movements(block):
    return block.get('movements', []) if isinstance(block, dict) else list(block.movements.all())


def _movement_payload(movement):
    if isinstance(movement, dict):
        return movement
    return {
        'movement_slug': movement.movement_slug,
        'movement_label_raw': movement.movement_label_raw,
        'sets': movement.sets,
        'reps_spec': movement.reps_spec,
        'load_spec': movement.load_spec,
        'notes': movement.notes,
        'is_scaled_alternative': getattr(movement, 'is_scaled_alternative', False),
    }


def _summarize_load_projection(movement_payload):
    load_spec = (movement_payload.get('load_spec') or '').strip()
    if not load_spec:
        return WorkoutLoadType.FREE, None, ''
    percentage_match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*%\s*(?:do\s*)?(?:RM)?', load_spec, flags=re.IGNORECASE)
    if percentage_match:
        return WorkoutLoadType.PERCENTAGE_OF_RM, Decimal(percentage_match.group(1).replace(',', '.')), ''
    fixed_match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*(?:kg)?', load_spec, flags=re.IGNORECASE)
    if fixed_match:
        return WorkoutLoadType.FIXED_KG, Decimal(fixed_match.group(1).replace(',', '.')), ''
    try:
        return WorkoutLoadType.FIXED_KG, Decimal(load_spec.replace(',', '.')), ''
    except Exception:
        return WorkoutLoadType.FREE, None, ''


def build_projection_preview(*, weekly_plan, target_week_start, class_types):
    days = _extract_plan_days(weekly_plan)
    class_types = list(class_types or [ClassType.CROSS])
    filter_class_types = _expand_projection_class_types(class_types)
    range_start, range_end = _week_range(target_week_start)
    sessions_in_week = ClassSession.objects.filter(scheduled_at__gte=range_start, scheduled_at__lt=range_end)
    sessions_in_week_total = sessions_in_week.count()
    sessions_canceled_total = sessions_in_week.filter(status=SessionStatus.CANCELED).count()
    canceled_session_times = list(_session_track_filter(
        sessions_in_week.filter(status=SessionStatus.CANCELED), weekly_plan, class_types,
    ).values_list('scheduled_at', flat=True))
    canceled_by_weekday = {}
    for scheduled_at in canceled_session_times:
        weekday = timezone.localtime(scheduled_at).weekday()
        canceled_by_weekday[weekday] = canceled_by_weekday.get(weekday, 0) + 1
    sessions_canceled_selected_total = len(canceled_session_times)
    sessions = (
        _session_track_filter(
            ClassSession.objects.select_related('coach', 'workout', 'workout_program')
            .filter(scheduled_at__gte=range_start, scheduled_at__lt=range_end),
            weekly_plan, class_types,
        )
        .exclude(status=SessionStatus.CANCELED)
        .order_by('scheduled_at', 'id')
    )
    entries = []
    totals = {
        'sessions_found': 0,
        'sessions_creatable': 0,
        'sessions_skipped': 0,
        'sessions_with_existing_workout': 0,
        'sessions_without_day_plan': 0,
        'discarded_blocks': 0,
        'load_notes': 0,
    }
    type_summary = {class_type: {'sessions_found': 0, 'sessions_creatable': 0, 'discarded_blocks': 0} for class_type in filter_class_types}
    for session in sessions:
        totals['sessions_found'] += 1
        type_summary.setdefault(session.class_type, {'sessions_found': 0, 'sessions_creatable': 0, 'discarded_blocks': 0})
        type_summary[session.class_type]['sessions_found'] += 1
        session_weekday = timezone.localtime(session.scheduled_at).weekday()
        day_plan = days.get(session_weekday)
        if day_plan is None:
            totals['sessions_without_day_plan'] += 1
            totals['sessions_skipped'] += 1
            entries.append(
                {
                    'session_id': session.id,
                    'session_title': session.title,
                    'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
                    'weekday_label': _WEEKDAY_TITLES[session_weekday],
                    'weekday_index': session_weekday,
                    'class_type': session.class_type,
                    'status': 'skip_no_day_plan',
                    'discarded_blocks': [],
                    'projection_blocks': [],
                    'load_projection_notes': [],
                    'reason': 'Nao existe dia correspondente no plano para esta aula.',
                }
            )
            continue
        if hasattr(session, 'workout'):
            totals['sessions_with_existing_workout'] += 1
            totals['sessions_skipped'] += 1
            entries.append(
                {
                    'session_id': session.id,
                    'session_title': session.title,
                    'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
                    'weekday_label': _WEEKDAY_TITLES[session_weekday],
                    'weekday_index': session_weekday,
                    'class_type': session.class_type,
                    'status': 'skip_existing_workout',
                    'discarded_blocks': [],
                    'projection_blocks': [],
                    'load_projection_notes': [],
                    'reason': 'A aula ja possui WOD. Politica atual: pular sem sobrescrever.',
                }
            )
            continue

        allowed_kinds = _compatible_kinds_for_session(session)
        projection_blocks = []
        discarded_blocks = []
        load_projection_notes = []
        for block in _normalize_plan_blocks(day_plan):
            kind = _block_kind(block)
            if kind not in allowed_kinds:
                discarded_blocks.append({
                    'kind': kind,
                    'title': _block_title(block) or kind,
                    'reason': f'Bloco incompatível com {session.class_type}.',
                })
                totals['discarded_blocks'] += 1
                type_summary[session.class_type]['discarded_blocks'] += 1
                continue
            movement_rows = []
            for movement in _block_movements(block):
                payload = _movement_payload(movement)
                load_type, load_value, load_note = _summarize_load_projection(payload)
                if load_note:
                    load_projection_notes.append(f"{payload.get('movement_label_raw')}: {load_note}")
                    totals['load_notes'] += 1
                movement_rows.append(
                    {
                        'movement_slug': payload.get('movement_slug') or '',
                        'movement_label_raw': payload.get('movement_label_raw') or '',
                        'sets': payload.get('sets'),
                        'reps_spec': payload.get('reps_spec') or '',
                        'load_spec': payload.get('load_spec') or '',
                        'notes': payload.get('notes') or '',
                        'is_scaled_alternative': bool(payload.get('is_scaled_alternative')),
                        'projected_load_type': load_type,
                        'projected_load_value': str(load_value) if load_value is not None else '',
                    }
                )
            projection_blocks.append(
                {
                    'kind': kind,
                    'title': _block_title(block) or kind,
                    'notes': _block_notes(block) or '',
                    'timecap_min': _block_value(block, 'timecap_min'),
                    'rounds': _block_value(block, 'rounds'),
                    'interval_seconds': _block_value(block, 'interval_seconds'),
                    'score_type': _block_value(block, 'score_type') or '',
                    'format_spec': _block_value(block, 'format_spec') or '',
                    'movement_count': len(movement_rows),
                    'movements': movement_rows,
                }
            )

        status = 'ready'
        reason = ''
        if not projection_blocks:
            status = 'skip_no_compatible_blocks'
            reason = 'Todos os blocos foram descartados pelas regras de compatibilidade.'
            totals['sessions_skipped'] += 1
        else:
            totals['sessions_creatable'] += 1
            type_summary[session.class_type]['sessions_creatable'] += 1
        entries.append(
            {
                'session_id': session.id,
                'session_title': session.title,
                'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
                'weekday_label': _WEEKDAY_TITLES[session_weekday],
                'weekday_index': session_weekday,
                'class_type': session.class_type,
                'status': status,
                'discarded_blocks': discarded_blocks,
                'projection_blocks': projection_blocks,
                'load_projection_notes': load_projection_notes,
                'reason': reason,
            }
        )
    return {
        'target_week_start': target_week_start,
        'workout_program_label': getattr(getattr(weekly_plan, 'workout_program', None), 'name', ''),
        'workout_program_slug': getattr(getattr(weekly_plan, 'workout_program', None), 'slug', ''),
        'class_types': class_types,
        'entries': entries,
        'totals': totals,
        'type_summary': type_summary,
        'sessions_in_week_total': sessions_in_week_total,
        'sessions_active_in_week_total': sessions_in_week_total - sessions_canceled_total,
        'sessions_canceled_total': sessions_canceled_total,
        'sessions_canceled_selected_total': sessions_canceled_selected_total,
        'canceled_by_weekday': canceled_by_weekday,
        'collision_policy': 'skip_existing_workout',
    }


def _parse_reps(reps_spec):
    if not reps_spec:
        return None
    if re_match := re.match(r'^\d+$', reps_spec.strip()):
        return int(re_match.group(0))
    return None


def _projection_request_fingerprint(*, weekly_plan, target_week_start, class_types, actor):
    request_identity = {
        'actor_id': actor.pk,
        'class_types': sorted(set(class_types)),
        'plan_id': weekly_plan.pk,
        'workout_program_id': getattr(weekly_plan, 'workout_program_id', None),
        'plan_label': weekly_plan.label,
        'plan_week_start': weekly_plan.week_start.isoformat(),
        'parsed_payload': weekly_plan.parsed_payload or {},
        'target_week_start': target_week_start.isoformat(),
    }
    serialized = json.dumps(
        request_identity,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def _replay_projection_batch(*, batch, fingerprint, weekly_plan, target_week_start, class_types):
    if batch.request_fingerprint != fingerprint:
        raise ValidationError('Esta chave de envio já foi usada para outra semana ou outro treino. Atualize a prévia e tente novamente.')
    if batch.undone_at:
        raise ValidationError('Este envio já foi desfeito. Atualize a prévia antes de distribuir novamente.')
    if batch.sessions_created != batch.session_workouts.count():
        raise ValidationError('O resultado deste envio foi alterado depois da distribuição. Atualize a prévia para conferir o estado atual.')

    preview = build_projection_preview(
        weekly_plan=weekly_plan,
        target_week_start=target_week_start,
        class_types=class_types,
    )
    preview['totals']['sessions_pending_approval'] = batch.session_workouts.filter(
        status=SessionWorkoutStatus.PENDING_APPROVAL,
    ).count()
    preview['totals']['sessions_published'] = batch.session_workouts.filter(
        status=SessionWorkoutStatus.PUBLISHED,
    ).count()
    preview['idempotent_replay'] = True
    return batch, preview


@transaction.atomic
def project_plan_to_sessions(*, weekly_plan, target_week_start, class_types, actor, idempotency_key=None):
    # Serialize concurrent distribution attempts for the same scheduled classes.
    # Replays with the same request key return the original batch; independent
    # requests rebuild the preview under lock and skip the committed collision.
    range_start, range_end = _week_range(target_week_start)
    filter_class_types = _expand_projection_class_types(class_types)
    list(
        _session_track_filter(
            ClassSession.objects.select_for_update().filter(
            scheduled_at__gte=range_start,
            scheduled_at__lt=range_end,
            ), weekly_plan, class_types,
        )
        .order_by('scheduled_at', 'id')
        .values_list('id', flat=True)
    )
    fingerprint = _projection_request_fingerprint(
        weekly_plan=weekly_plan,
        target_week_start=target_week_start,
        class_types=class_types,
        actor=actor,
    )
    if idempotency_key:
        existing_batch = ReplicationBatch.objects.select_for_update().filter(
            idempotency_key=idempotency_key,
        ).first()
        if existing_batch:
            return _replay_projection_batch(
                batch=existing_batch,
                fingerprint=fingerprint,
                weekly_plan=weekly_plan,
                target_week_start=target_week_start,
                class_types=class_types,
            )
    preview = build_projection_preview(
        weekly_plan=weekly_plan,
        target_week_start=target_week_start,
        class_types=class_types,
    )
    if not preview['totals']['sessions_creatable']:
        raise ValidationError('Nenhuma aula nova esta pronta para receber WOD. Atualize a previa antes de distribuir.')

    try:
        with transaction.atomic():
            batch = ReplicationBatch.objects.create(
                weekly_plan=weekly_plan,
                created_by=actor,
                class_type_filter=list(class_types),
                target_week_start=target_week_start,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                sessions_targeted=preview['totals']['sessions_found'],
                sessions_created=0,
            )
    except IntegrityError:
        if not idempotency_key:
            raise
        existing_batch = ReplicationBatch.objects.select_for_update().filter(
            idempotency_key=idempotency_key,
        ).first()
        if not existing_batch:
            raise
        return _replay_projection_batch(
            batch=existing_batch,
            fingerprint=fingerprint,
            weekly_plan=weekly_plan,
            target_week_start=target_week_start,
            class_types=class_types,
        )
    created_count = 0
    pending_approval_count = 0
    published_count = 0
    session_ids = [entry['session_id'] for entry in preview['entries'] if entry['status'] == 'ready']
    sessions_by_id = {
        session.id: session
        for session in ClassSession.objects.select_for_update().filter(id__in=session_ids).order_by('scheduled_at', 'id')
    }
    for entry in preview['entries']:
        if entry['status'] != 'ready':
            continue
        session = sessions_by_id[entry['session_id']]
        workout = SessionWorkout.objects.create(
            session=session,
            replication_batch=batch,
            title=_session_workout_title(weekly_plan=weekly_plan, session=session),
            coach_notes='',
            status=SessionWorkoutStatus.DRAFT,
            created_by=actor,
            version=1,
            structured_payload={
                'format_version': 'weekly_wod_projection_v1',
                'source': 'weekly_smart_paste',
                'weekly_plan_id': weekly_plan.id,
                'week_start': weekly_plan.week_start.isoformat(),
                'blocks': entry['projection_blocks'],
            },
        )
        for block_index, block_entry in enumerate(entry['projection_blocks'], start=1):
            workout_block = SessionWorkoutBlock.objects.create(
                workout=workout,
                kind=block_entry['kind'] if block_entry['kind'] in {choice[0] for choice in SessionWorkoutBlock._meta.get_field('kind').choices} else 'custom',
                title=block_entry['title'],
                notes=block_entry['notes'],
                timecap_min=block_entry['timecap_min'],
                rounds=block_entry['rounds'],
                interval_seconds=block_entry['interval_seconds'],
                score_type=block_entry['score_type'],
                format_spec=block_entry['format_spec'],
                sort_order=block_index,
            )
            for movement_index, movement_entry in enumerate(block_entry['movements'], start=1):
                payload = {
                    'movement_slug': movement_entry['movement_slug'] or 'custom',
                    'movement_label': movement_entry['movement_label_raw'] or 'Movimento',
                    'sets': movement_entry['sets'],
                    'reps': _parse_reps(movement_entry['reps_spec']),
                    'reps_spec': movement_entry['reps_spec'],
                    'load_type': movement_entry['projected_load_type'],
                    'load_value': Decimal(movement_entry['projected_load_value']) if movement_entry['projected_load_value'] else None,
                    'load_spec': movement_entry['load_spec'],
                    'is_scaled_alternative': movement_entry['is_scaled_alternative'],
                    'notes': movement_entry['notes'],
                    'sort_order': movement_index,
                }
                SessionWorkoutMovement.objects.create(block=workout_block, **payload)
        # Smart Paste never bypasses the box approval policy. Coach-created
        # WODs enter the approval queue; trusted-author policies may publish
        # directly only when the normal submission router permits it.
        submission = route_workout_submission(actor=actor, workout=workout, source='smart_paste')
        if submission['status'] == 'pending_approval':
            pending_approval_count += 1
        elif submission['status'] == 'published':
            published_count += 1
        created_count += 1
    batch.sessions_created = created_count
    batch.save(update_fields=['sessions_created', 'updated_at'])
    preview['totals']['sessions_pending_approval'] = pending_approval_count
    preview['totals']['sessions_published'] = published_count
    return batch, preview


__all__ = ['CLASS_TYPE_COMPATIBILITY', 'build_projection_preview', 'project_plan_to_sessions']
