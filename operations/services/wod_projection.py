"""
ARQUIVO: projeção de plano semanal para WODs draft por aula.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
import re

from django.db import transaction
from django.utils import timezone

from operations.models import ClassSession, ClassType
from student_app.models import (
    PlanBlockKind,
    ReplicationBatch,
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutStatus,
    WorkoutLoadType,
)


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
    }


def _summarize_load_projection(movement_payload):
    load_spec = (movement_payload.get('load_spec') or '').strip()
    if not load_spec:
        return WorkoutLoadType.FREE, None, ''
    if load_spec.endswith('%'):
        return WorkoutLoadType.PERCENTAGE_OF_RM, Decimal(load_spec[:-1].replace(',', '.')), ''
    if '/' in load_spec:
        return WorkoutLoadType.FREE, None, f'Carga alvo preservada em nota: {load_spec}'
    try:
        return WorkoutLoadType.FIXED_KG, Decimal(load_spec.replace(',', '.')), ''
    except Exception:
        return WorkoutLoadType.FREE, None, f'Carga original preservada em nota: {load_spec}'


def build_projection_preview(*, weekly_plan, target_week_start, class_types):
    days = _extract_plan_days(weekly_plan)
    if not class_types:
        class_types = [ClassType.CROSS]
    range_start, range_end = _week_range(target_week_start)
    sessions = (
        ClassSession.objects.select_related('coach')
        .select_related('workout')
        .filter(scheduled_at__gte=range_start, scheduled_at__lt=range_end, class_type__in=class_types)
        .order_by('scheduled_at', 'id')
    )
    entries = []
    totals = {
        'sessions_found': 0,
        'sessions_creatable': 0,
        'sessions_with_existing_workout': 0,
        'sessions_without_day_plan': 0,
        'discarded_blocks': 0,
        'load_notes': 0,
    }
    type_summary = {class_type: {'sessions_found': 0, 'sessions_creatable': 0, 'discarded_blocks': 0} for class_type in class_types}
    for session in sessions:
        totals['sessions_found'] += 1
        type_summary[session.class_type]['sessions_found'] += 1
        session_weekday = timezone.localtime(session.scheduled_at).weekday()
        day_plan = days.get(session_weekday)
        if day_plan is None:
            totals['sessions_without_day_plan'] += 1
            entries.append(
                {
                    'session_id': session.id,
                    'session_title': session.title,
                    'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
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
            entries.append(
                {
                    'session_id': session.id,
                    'session_title': session.title,
                    'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
                    'class_type': session.class_type,
                    'status': 'skip_existing_workout',
                    'discarded_blocks': [],
                    'projection_blocks': [],
                    'load_projection_notes': [],
                    'reason': 'A aula ja possui WOD. Politica atual: pular sem sobrescrever.',
                }
            )
            continue

        allowed_kinds = _compatible_kinds_for(session.class_type)
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
                        'reps_spec': payload.get('reps_spec') or '',
                        'load_spec': payload.get('load_spec') or '',
                        'projected_load_type': load_type,
                        'projected_load_value': str(load_value) if load_value is not None else '',
                    }
                )
            projection_blocks.append(
                {
                    'kind': kind,
                    'title': _block_title(block) or kind,
                    'notes': _block_notes(block) or '',
                    'movement_count': len(movement_rows),
                    'movements': movement_rows,
                }
            )

        status = 'ready'
        reason = ''
        if not projection_blocks:
            status = 'skip_no_compatible_blocks'
            reason = 'Todos os blocos foram descartados pelas regras de compatibilidade.'
        else:
            totals['sessions_creatable'] += 1
            type_summary[session.class_type]['sessions_creatable'] += 1
        entries.append(
            {
                'session_id': session.id,
                'session_title': session.title,
                'session_date_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
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
        'class_types': class_types,
        'entries': entries,
        'totals': totals,
        'type_summary': type_summary,
        'collision_policy': 'skip_existing_workout',
    }


def _parse_reps(reps_spec):
    if not reps_spec:
        return None
    if re_match := re.match(r'^\d+$', reps_spec.strip()):
        return int(re_match.group(0))
    return None


@transaction.atomic
def project_plan_to_sessions(*, weekly_plan, target_week_start, class_types, actor):
    preview = build_projection_preview(
        weekly_plan=weekly_plan,
        target_week_start=target_week_start,
        class_types=class_types,
    )
    batch = ReplicationBatch.objects.create(
        weekly_plan=weekly_plan,
        created_by=actor,
        class_type_filter=list(class_types),
        sessions_targeted=preview['totals']['sessions_found'],
        sessions_created=0,
    )
    created_count = 0
    session_ids = [entry['session_id'] for entry in preview['entries'] if entry['status'] == 'ready']
    sessions_by_id = {
        session.id: session
        for session in ClassSession.objects.filter(id__in=session_ids).order_by('scheduled_at', 'id')
    }
    for entry in preview['entries']:
        if entry['status'] != 'ready':
            continue
        session = sessions_by_id[entry['session_id']]
        workout = SessionWorkout.objects.create(
            session=session,
            replication_batch=batch,
            title=weekly_plan.label or session.title,
            coach_notes=f'Gerado pelo Smart Paste semanal ({weekly_plan.week_start:%d/%m/%Y}).',
            status=SessionWorkoutStatus.DRAFT,
            created_by=actor,
            version=1,
        )
        for block_index, block_entry in enumerate(entry['projection_blocks'], start=1):
            workout_block = SessionWorkoutBlock.objects.create(
                workout=workout,
                kind=block_entry['kind'] if block_entry['kind'] in {choice[0] for choice in SessionWorkoutBlock._meta.get_field('kind').choices} else 'custom',
                title=block_entry['title'],
                notes=block_entry['notes'],
                sort_order=block_index,
            )
            for movement_index, movement_entry in enumerate(block_entry['movements'], start=1):
                payload = {
                    'movement_slug': movement_entry['movement_slug'] or 'custom',
                    'movement_label': movement_entry['movement_label_raw'] or 'Movimento',
                    'sets': None,
                    'reps': _parse_reps(movement_entry['reps_spec']),
                    'load_type': movement_entry['projected_load_type'],
                    'load_value': Decimal(movement_entry['projected_load_value']) if movement_entry['projected_load_value'] else None,
                    'notes': movement_entry['load_spec'],
                    'sort_order': movement_index,
                }
                SessionWorkoutMovement.objects.create(block=workout_block, **payload)
        created_count += 1
    batch.sessions_created = created_count
    batch.save(update_fields=['sessions_created', 'updated_at'])
    return batch, preview


__all__ = ['CLASS_TYPE_COMPATIBILITY', 'build_projection_preview', 'project_plan_to_sessions']
