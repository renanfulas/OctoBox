"""
ARQUIVO: aplicacao e leitura do modelo persistente de templates de WOD.

POR QUE ELE EXISTE:
- centraliza o uso do modelo WorkoutTemplate sem espalhar a logica pelo editor.
"""

from urllib.parse import urlencode

from django.db import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_OWNER
from operations.models import WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from student_app.models import SessionWorkout, SessionWorkoutBlock, SessionWorkoutMovement, SessionWorkoutRevisionEvent, SessionWorkoutStatus

from .workout_support import create_workout_revision, record_workout_audit
from .services.wod_projection import _summarize_load_projection


def _safe_workout_template_queryset():
    return WorkoutTemplate.objects.all()


def _safe_list(queryset):
    try:
        return list(queryset)
    except (OperationalError, ProgrammingError):
        return []


def _safe_aggregate(queryset, **kwargs):
    try:
        return queryset.aggregate(**kwargs)
    except (OperationalError, ProgrammingError):
        return {key: 0 for key in kwargs}


def _build_template_management_href(*, template_id, query=''):
    href = reverse('workout-template-management')
    if query:
        href = f'{href}?{urlencode({"q": query})}'
    return f'{href}#template-card-{template_id}'


def build_persisted_workout_template_options(*, current_role_slug, actor, limit=12):
    queryset = _safe_workout_template_queryset().filter(is_active=True).order_by('-is_featured', '-usage_count', '-last_used_at', 'name', '-updated_at')
    if current_role_slug == ROLE_COACH:
        queryset = queryset.filter(created_by=actor)
    options = []
    for template in _safe_list(queryset[:limit]):
        can_manage = current_role_slug in {ROLE_COACH, ROLE_OWNER}
        all_blocks = list(template.blocks.all())
        block_count = len(all_blocks)
        movement_count = sum(block.movements.count() for block in all_blocks)
        preview_blocks = []
        load_types = set()
        for block in all_blocks[:2]:
            preview_movements = list(block.movements.all()[:2])
            preview_blocks.append(
                {
                    'title': block.title,
                    'kind': block.kind,
                    'kind_label': block.get_kind_display(),
                    'movement_preview': ', '.join(movement.movement_label for movement in preview_movements),
                }
            )
            for movement in block.movements.all():
                load_types.add(movement.load_type)
        options.append(
            {
                'id': template.id,
                'label': template.name,
                'coach_label': (
                    template.created_by.get_full_name() or template.created_by.username
                    if template.created_by
                    else 'Sem autor'
                ),
                'description': template.description,
                'is_featured': template.is_featured,
                'is_trusted': template.is_trusted,
                'block_count': block_count,
                'movement_count': movement_count,
                'summary': f'{block_count} bloco(s) ? {movement_count} movimento(s)',
                'preview_blocks': tuple(preview_blocks),
                'has_percentage_rm': 'percentage_of_rm' in load_types,
                'has_fixed_load': 'fixed_kg' in load_types,
                'usage_count': template.usage_count,
                'last_used_label': template.last_used_at.strftime('%d/%m %H:%M') if template.last_used_at else 'Nunca usado',
                'is_cold': template.usage_count == 0,
                'can_manage': can_manage,
                'management_href': _build_template_management_href(template_id=template.id, query=template.name) if can_manage else '',
                'duplicate_action': reverse('workout-template-duplicate', args=[template.id]) if can_manage else '',
                'duplicate_name': f'{template.name} copia',
            }
        )
    return tuple(options)


def apply_persisted_workout_template(*, actor, template, target_session):
    target_workout = getattr(target_session, 'workout', None)
    if target_workout is not None and target_workout.blocks.exists():
        return {
            'ok': False,
            'reason': 'target_has_blocks',
            'target_block_count': target_workout.blocks.count(),
            'target_movement_count': sum(block.movements.count() for block in target_workout.blocks.all()),
        }

    if target_workout is None:
        target_workout = SessionWorkout.objects.create(
            session=target_session,
            title=template.name,
            coach_notes='Base aplicada a partir de template persistente.',
            status=SessionWorkoutStatus.DRAFT,
            created_by=actor,
            version=1,
        )
    else:
        target_workout.title = template.name
        target_workout.status = SessionWorkoutStatus.DRAFT
        target_workout.version += 1
        target_workout.save(update_fields=['title', 'status', 'version', 'updated_at'])

    for block in template.blocks.all():
        created_block = SessionWorkoutBlock.objects.create(
            workout=target_workout,
            kind=block.kind,
            title=block.title,
            notes=block.notes,
            sort_order=block.sort_order,
        )
        for movement in block.movements.all():
            SessionWorkoutMovement.objects.create(
                block=created_block,
                movement_slug=movement.movement_slug,
                movement_label=movement.movement_label,
                sets=movement.sets,
                reps=movement.reps,
                load_type=movement.load_type,
                load_value=movement.load_value,
                notes=movement.notes,
                sort_order=movement.sort_order,
            )

    create_workout_revision(
        workout=target_workout,
        actor=actor,
        event=SessionWorkoutRevisionEvent.DUPLICATED,
        extra_snapshot={'template_id': template.id, 'template_mode': 'persisted_template'},
    )
    record_workout_audit(
        actor=actor,
        workout=target_workout,
        action='session_workout_persisted_template_applied',
        description='Template persistente de WOD aplicado na aula.',
        metadata={'template_id': template.id, 'session_id': target_workout.session_id, 'version': target_workout.version},
    )
    template.usage_count += 1
    template.last_used_at = timezone.now()
    template.save(update_fields=['usage_count', 'last_used_at', 'updated_at'])
    return {'ok': True, 'reason': 'applied', 'workout': target_workout}


def create_persisted_template_from_workout(*, actor, source_workout, name):
    template = WorkoutTemplate.objects.create(
        name=name,
        created_by=actor,
        source_workout=source_workout,
        is_active=True,
    )
    for block in source_workout.blocks.all():
        created_block = WorkoutTemplateBlock.objects.create(
            template=template,
            kind=block.kind,
            title=block.title,
            notes=block.notes,
            sort_order=block.sort_order,
        )
        for movement in block.movements.all():
            WorkoutTemplateMovement.objects.create(
                block=created_block,
                movement_slug=movement.movement_slug,
                movement_label=movement.movement_label,
                sets=movement.sets,
                reps=movement.reps,
                load_type=movement.load_type,
                load_value=movement.load_value,
                notes=movement.notes,
                sort_order=movement.sort_order,
            )
    return template


def create_persisted_template_from_weekly_plan(*, actor, weekly_plan, name, description=''):
    parsed_payload = getattr(weekly_plan, 'parsed_payload', {}) or {}
    days = parsed_payload.get('days') or []
    template = WorkoutTemplate.objects.create(
        name=name,
        description=(description or '').strip(),
        created_by=actor,
        is_active=True,
        is_trusted=False,
    )
    block_order = 1
    for day in days:
        weekday_label = (day.get('weekday_label') or '').strip()
        for block in day.get('blocks', []):
            block_kind = (block.get('kind') or 'custom').strip()
            if block_kind not in {choice[0] for choice in WorkoutTemplateBlock._meta.get_field('kind').choices}:
                block_kind = 'custom'
            block_title = (block.get('title') or '').strip() or block_kind.title()
            block_notes_parts = []
            if weekday_label:
                block_notes_parts.append(f'Dia base: {weekday_label}')
            for extra in (block.get('format_spec'), block.get('notes')):
                extra_text = (extra or '').strip()
                if extra_text:
                    block_notes_parts.append(extra_text)
            created_block = WorkoutTemplateBlock.objects.create(
                template=template,
                kind=block_kind,
                title=block_title,
                notes=' | '.join(block_notes_parts),
                sort_order=block_order,
            )
            block_order += 1
            for movement_index, movement in enumerate(block.get('movements', []), start=1):
                load_type, load_value, load_note = _summarize_load_projection(movement)
                notes_parts = []
                load_spec = (movement.get('load_spec') or '').strip()
                movement_note = (movement.get('notes') or '').strip()
                if load_note:
                    notes_parts.append(load_note)
                elif load_spec and load_type == 'free':
                    notes_parts.append(load_spec)
                if movement_note:
                    notes_parts.append(movement_note)
                WorkoutTemplateMovement.objects.create(
                    block=created_block,
                    movement_slug=(movement.get('movement_slug') or 'custom').strip() or 'custom',
                    movement_label=(movement.get('movement_label_raw') or 'Movimento').strip() or 'Movimento',
                    sets=None,
                    reps=_parse_reps(movement.get('reps_spec') or ''),
                    load_type=load_type,
                    load_value=load_value,
                    notes=' | '.join(notes_parts)[:255],
                    sort_order=movement_index,
                )
    return template


def _parse_reps(reps_spec):
    normalized = (reps_spec or '').strip()
    if normalized.isdigit():
        return int(normalized)
    return None


def duplicate_persisted_template(*, actor, template, name=None):
    duplicate_name = (name or '').strip() or f'{template.name} copia'
    duplicated_template = WorkoutTemplate.objects.create(
        name=duplicate_name,
        description=template.description,
        created_by=actor,
        source_workout=template.source_workout,
        is_active=template.is_active,
        is_featured=False,
        is_trusted=template.is_trusted,
    )
    for block in template.blocks.all():
        duplicated_block = WorkoutTemplateBlock.objects.create(
            template=duplicated_template,
            kind=block.kind,
            title=block.title,
            notes=block.notes,
            sort_order=block.sort_order,
        )
        for movement in block.movements.all():
            WorkoutTemplateMovement.objects.create(
                block=duplicated_block,
                movement_slug=movement.movement_slug,
                movement_label=movement.movement_label,
                sets=movement.sets,
                reps=movement.reps,
                load_type=movement.load_type,
                load_value=movement.load_value,
                notes=movement.notes,
                sort_order=movement.sort_order,
            )
    return duplicated_template


def delete_persisted_template(*, template):
    template_name = template.name
    template.delete()
    return {'deleted_name': template_name}


def build_workout_template_management_summary(*, current_role_slug, actor):
    queryset = _safe_workout_template_queryset()
    if current_role_slug == ROLE_COACH:
        queryset = queryset.filter(created_by=actor)
    aggregate = _safe_aggregate(
        queryset,
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        featured=Count('id', filter=Q(is_featured=True)),
        trusted=Count('id', filter=Q(is_trusted=True)),
        cold=Count('id', filter=Q(usage_count=0)),
    )
    return {
        'total': aggregate['total'] or 0,
        'active': aggregate['active'] or 0,
        'featured': aggregate['featured'] or 0,
        'trusted': aggregate['trusted'] or 0,
        'cold': aggregate['cold'] or 0,
    }


def build_manageable_workout_templates(*, current_role_slug, actor, active_only=False, featured_only=False, query=''):
    queryset = _safe_workout_template_queryset().order_by('-is_featured', '-is_active', '-usage_count', '-last_used_at', 'name', '-updated_at')
    if current_role_slug == ROLE_COACH:
        queryset = queryset.filter(created_by=actor)
    if active_only:
        queryset = queryset.filter(is_active=True)
    if featured_only:
        queryset = queryset.filter(is_featured=True)
    search_query = (query or '').strip()
    if search_query:
        queryset = queryset.filter(name__icontains=search_query)
    templates = []
    for template in _safe_list(queryset):
        is_mine = template.created_by_id == getattr(actor, 'id', None)
        block_count = template.blocks.count()
        movement_count = sum(block.movements.count() for block in template.blocks.all())
        blocks = []
        for block in template.blocks.all():
            movements = []
            for movement in block.movements.all():
                movements.append(
                    {
                        'id': movement.id,
                        'movement_slug': movement.movement_slug,
                        'movement_label': movement.movement_label,
                        'sets': movement.sets,
                        'reps': movement.reps,
                        'load_type': movement.load_type,
                        'load_value': movement.load_value,
                        'notes': movement.notes,
                        'sort_order': movement.sort_order,
                    }
                )
            blocks.append(
                {
                    'id': block.id,
                    'title': block.title,
                    'kind': block.kind,
                    'notes': block.notes,
                    'sort_order': block.sort_order,
                    'movements': tuple(movements),
                }
            )
        templates.append(
            {
                'id': template.id,
                'name': template.name,
                'delete_label': f'Excluir {template.name}',
                'duplicate_label': f'Duplicar {template.name}',
                'coach_label': (
                    template.created_by.get_full_name() or template.created_by.username
                    if template.created_by
                    else 'Sem autor'
                ),
                'is_mine': is_mine,
                'description': template.description,
                'is_active': template.is_active,
                'is_featured': template.is_featured,
                'is_trusted': template.is_trusted,
                'usage_count': template.usage_count,
                'last_used_label': template.last_used_at.strftime('%d/%m %H:%M') if template.last_used_at else 'Nunca usado',
                'is_cold': template.usage_count == 0,
                'block_count': block_count,
                'movement_count': movement_count,
                'blocks': tuple(blocks),
            }
        )
    return tuple(templates)


__all__ = [
    'apply_persisted_workout_template',
    'build_manageable_workout_templates',
    'build_persisted_workout_template_options',
    'build_workout_template_management_summary',
    'create_persisted_template_from_workout',
    'create_persisted_template_from_weekly_plan',
    'delete_persisted_template',
    'duplicate_persisted_template',
]
