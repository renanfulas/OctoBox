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
)
from operations.models import ClassType
from operations.services.wod_paste_parser import load_wod_movement_dictionary
from operations.services.wod_replication_batches import batch_can_be_undone
from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_hero, build_page_payload
from student_app.models import WeeklyWodPlan, WeeklyWodPlanStatus

from .workout_corridor_navigation import build_workout_corridor_tabs


def _default_week_start(today):
    return today - timedelta(days=today.weekday())


def load_latest_weekly_wod_plan_for_user(*, user):
    if not getattr(user, 'is_authenticated', False):
        return None
    return WeeklyWodPlan.objects.filter(created_by=user).order_by('-updated_at', '-id').first()


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
        assets=build_page_assets(css=['css/design-system/operations.css']),
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
):
    weekly_plan = plan or load_latest_weekly_wod_plan_for_user(user=request.user)
    week_start = getattr(weekly_plan, 'week_start', None) or _default_week_start(today)
    form = form or WeeklyWodSmartPasteForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'week_start': week_start,
            'label': getattr(weekly_plan, 'label', ''),
            'source_text': getattr(weekly_plan, 'source_text', ''),
        }
    )
    projection_form = projection_form or WeeklyWodProjectionForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'target_week_start': week_start,
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
        'smart_paste_step': 3 if projection_preview else (2 if parsed_payload.get('days') else 1),
        'projection_form': projection_form,
        'projection_preview': projection_preview,
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


__all__ = ['build_weekly_wod_smart_paste_context', 'load_latest_weekly_wod_plan_for_user']
