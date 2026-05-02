"""
ARQUIVO: contexto da superficie de Smart Paste semanal do corredor de WOD.
"""

from __future__ import annotations

from datetime import timedelta

from django.urls import reverse

from operations.forms import (
    WeeklyWodProjectionForm,
    WeeklyWodReviewMovementForm,
    WeeklyWodSmartPasteForm,
    WeeklyWodUndoReplicationForm,
    WorkoutCreateStoredTemplateForm,
)
from operations.models import ClassType
from operations.services.wod_paste_parser import load_wod_movement_dictionary
from operations.services.wod_replication_batches import batch_can_be_undone
from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_hero, build_page_payload
from student_app.models import WeeklyWodPlan, WeeklyWodPlanStatus

from .workout_corridor_navigation import build_workout_corridor_tabs


def _default_week_start(today):
    return today - timedelta(days=today.weekday())


def _smart_paste_display_label(movement):
    label_raw = movement.get('movement_label_raw') or ''
    movement_slug = movement.get('movement_slug') or ''
    reps_spec = (movement.get('reps_spec') or '').strip()
    normalized_reps = reps_spec.lower()
    if movement_slug == 'run' and reps_spec and normalized_reps.isdigit():
        return f'{reps_spec}m run'
    return label_raw


def _decorate_preview_payload(parsed_payload):
    unresolved_items = []
    total_blocks = 0
    total_movements = 0
    first_unresolved_target_id = ''
    for day_index, day in enumerate(parsed_payload.get('days', [])):
        day_has_unresolved = False
        for block_index, block in enumerate(day.get('blocks', [])):
            total_blocks += 1
            for movement_index, movement in enumerate(block.get('movements', [])):
                movement['display_label'] = _smart_paste_display_label(movement)
                movement['review_target_id'] = f'review-item-{day_index}-{block_index}-{movement_index}'
                total_movements += 1
                if not movement.get('movement_slug'):
                    day_has_unresolved = True
                    first_unresolved_target_id = first_unresolved_target_id or movement['review_target_id']
                    unresolved_items.append(
                        {
                            'target_id': movement['review_target_id'],
                            'day_index': day_index,
                            'block_index': block_index,
                            'movement_index': movement_index,
                            'day_label': day.get('weekday_label', ''),
                            'block_kind': block.get('kind', ''),
                            'block_title': block.get('title') or block.get('kind', ''),
                            'movement_label_raw': movement.get('movement_label_raw', ''),
                            'movement_slug': movement.get('movement_slug') or '',
                            'reps_spec': movement.get('reps_spec') or '',
                            'load_spec': movement.get('load_spec') or '',
                            'notes': movement.get('notes') or '',
                            'display_label': movement.get('display_label') or movement.get('movement_label_raw', ''),
                        }
                    )
        day['has_unresolved'] = day_has_unresolved
    parsed_payload['summary'] = {
        'days_count': len(parsed_payload.get('days', [])),
        'blocks_count': total_blocks,
        'movements_count': total_movements,
        'unresolved_count': len(unresolved_items),
        'unresolved_items': unresolved_items[:8],
        'first_unresolved_target_id': first_unresolved_target_id,
        'current_unresolved_item': unresolved_items[0] if unresolved_items else None,
    }
    return parsed_payload


def load_surface_weekly_wod_plan_for_user(*, user, today):
    if not getattr(user, 'is_authenticated', False):
        return None
    return (
        WeeklyWodPlan.objects.filter(created_by=user, week_start=_default_week_start(today))
        .order_by('-updated_at', '-id')
        .first()
    )


def _build_page_payload(*, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-smart-paste',
            'title': 'Smart Paste semanal',
            'subtitle': 'Cole a semana, confira a leitura e feche um rascunho organizado.',
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Smart Paste',
                title='Cole o WOD semanal e revise antes de replicar.',
                copy='Esta etapa organiza o texto em dias, blocos e movimentos sem mexer ainda nas aulas reais.',
                actions=[
                    {'label': 'Abrir editor', 'href': reverse('workout-editor-home'), 'kind': 'secondary'},
                ],
                aria_label='Smart Paste semanal',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-smart-paste',
            'scope': 'operations-approval',
        },
        assets=build_page_assets(
            css=['css/design-system/operations.css'],
            js=['js/core/forms.js', 'js/operations/wod_smart_paste.js'],
        ),
    )


def build_weekly_wod_smart_paste_context(
    *,
    request,
    today,
    current_role,
    plan=None,
    form=None,
    projection_form=None,
    review_form=None,
    undo_form=None,
    parsed_payload=None,
    projection_preview=None,
    auto_open_review_target=None,
):
    week_start = _default_week_start(today)
    weekly_plan = plan or load_surface_weekly_wod_plan_for_user(user=request.user, today=today)
    form = form or WeeklyWodSmartPasteForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'week_start': week_start.strftime('%d/%m/%Y'),
            'label': getattr(weekly_plan, 'label', ''),
            'source_text': getattr(weekly_plan, 'source_text', ''),
        }
    )
    projection_form = projection_form or WeeklyWodProjectionForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'target_week_start': week_start.strftime('%d/%m/%Y'),
            'class_types': [ClassType.CROSS],
        }
    )
    latest_batch = weekly_plan.replication_batches.order_by('-created_at', '-id').first() if weekly_plan else None
    can_undo_batch, undo_reason = batch_can_be_undone(latest_batch)
    review_form = review_form or WeeklyWodReviewMovementForm(
        slug_choices=load_wod_movement_dictionary(),
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
        },
    )
    undo_form = undo_form or WeeklyWodUndoReplicationForm(
        initial={
            'batch_id': getattr(latest_batch, 'id', None),
        }
    )
    parsed_payload = parsed_payload if parsed_payload is not None else getattr(weekly_plan, 'parsed_payload', {}) or {}
    parsed_payload = _decorate_preview_payload(parsed_payload)
    current_unresolved_item = parsed_payload.get('summary', {}).get('current_unresolved_item')
    if current_unresolved_item and not getattr(review_form, 'is_bound', False):
        review_form = WeeklyWodReviewMovementForm(
            slug_choices=load_wod_movement_dictionary(),
            initial={
                'plan_id': getattr(weekly_plan, 'id', None),
                'day_index': current_unresolved_item['day_index'],
                'block_index': current_unresolved_item['block_index'],
                'movement_index': current_unresolved_item['movement_index'],
                'movement_label_raw': current_unresolved_item['movement_label_raw'],
                'movement_slug': current_unresolved_item['movement_slug'],
                'reps_spec': current_unresolved_item['reps_spec'],
                'load_spec': current_unresolved_item['load_spec'],
                'notes': current_unresolved_item['notes'],
            },
        )
    context = {
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='smart_paste',
            current_role_slug=current_role.slug,
        ),
        'smart_paste_form': form,
        'weekly_plan': weekly_plan,
        'smart_paste_preview': parsed_payload,
        'smart_paste_days': parsed_payload.get('days', []),
        'smart_paste_warnings': parsed_payload.get('parse_warnings', []),
        'smart_paste_summary': parsed_payload.get('summary', {}),
        'smart_paste_step': 3 if projection_preview else (2 if parsed_payload.get('days') else 1),
        'smart_paste_auto_open_review_target': auto_open_review_target or '',
        'projection_form': projection_form,
        'projection_preview': projection_preview,
        'create_stored_template_form': WorkoutCreateStoredTemplateForm(
            initial={
                'template_name': getattr(weekly_plan, 'label', '') or f"Template {week_start.strftime('%d/%m')}",
            }
        ),
        'template_management_href': reverse('workout-template-management'),
        'projection_selected_class_types': list(
            projection_form.data.getlist('class_types')
            if getattr(projection_form, 'data', None)
            else projection_form.initial.get('class_types', [])
        ),
        'review_form': review_form,
        'review_slug_choices': load_wod_movement_dictionary(),
        'undo_form': undo_form,
        'latest_replication_batch': latest_batch,
        'latest_replication_batch_can_undo': can_undo_batch,
        'latest_replication_batch_undo_reason': undo_reason,
        'weekly_plan_is_confirmed': getattr(weekly_plan, 'status', '') == WeeklyWodPlanStatus.CONFIRMED,
    }
    attach_page_payload(
        context,
        payload_key='operation_page',
        payload=_build_page_payload(current_role_slug=current_role.slug),
    )
    return context


__all__ = ['build_weekly_wod_smart_paste_context', 'load_surface_weekly_wod_plan_for_user']
