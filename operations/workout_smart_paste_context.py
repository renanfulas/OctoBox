"""
ARQUIVO: contexto da superficie de Smart Paste semanal do corredor de WOD.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone

from operations.forms import (
    WeeklyWodProjectionForm,
    WeeklyWodReviewMovementForm,
    WeeklyWodSmartPasteForm,
    WeeklyWodUndoReplicationForm,
    WorkoutCreateStoredTemplateForm,
)
from operations.models import ClassType, ClassSession, SessionStatus, WorkoutProgram
from operations.services.wod_generation_credits import get_or_create_current_ledger
from operations.services.wod_paste_parser import load_wod_movement_dictionary
from operations.services.wod_replication_batches import batch_can_be_undone
from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_hero, build_page_payload
from student_app.application.movement_references import lookup_movement_catalog_status
from student_app.models import WeeklyWodPlan, WeeklyWodPlanStatus

from .workout_corridor_navigation import build_workout_corridor_tabs


def _coming_monday(today):
    """Retorna a próxima segunda-feira. Se hoje for segunda, retorna hoje."""
    days_ahead = (7 - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


def _default_week_start(today):
    return _coming_monday(today)


def _class_type_for_program(program):
    if not program:
        return ClassType.CROSS
    valid_types = {choice for choice, _label in ClassType.choices}
    return program.slug if program.slug in valid_types else ClassType.CROSS


def _max_week_start(today, fallback_weeks: int = 52):
    """Retorna a segunda-feira da semana que contém a última aula agendada.

    Se não houver aulas futuras cadastradas, usa today + fallback_weeks como teto.
    """
    last_session = (
        ClassSession.objects
        .exclude(status=SessionStatus.CANCELED)
        .order_by('-scheduled_at')
        .values_list('scheduled_at', flat=True)
        .first()
    )
    if last_session is not None:
        last_date = timezone.localtime(last_session).date() if hasattr(last_session, 'tzinfo') else last_session
        # Monday of that week
        return max(_default_week_start(today), last_date - timedelta(days=last_date.weekday()))
    return today + timedelta(weeks=fallback_weeks)


def _smart_paste_display_label(movement):
    label_raw = movement.get('movement_label_raw') or ''
    movement_slug = movement.get('movement_slug') or ''
    reps_spec = (movement.get('reps_spec') or '').strip()
    normalized_reps = reps_spec.lower()
    if movement_slug == 'run' and reps_spec and normalized_reps.isdigit():
        return f'{reps_spec}m run'
    return label_raw


def count_unresolved_smart_paste_movements(parsed_payload):
    """Conta movimentos sem `movement_slug` resolvido, sem mutar o payload.

    Usada pelo view para recusar `confirm_plan` server-side quando ainda
    existem pendências — o botão "Confirmar rascunho semanal" no template
    fica `disabled` quando há pendências, mas isso é só client-side (HTML
    inspecionável); sem esta checagem, confirmar (e depois replicar) um
    plano com pendência grava o texto cru do coach ("agachamnto" etc.) como
    rótulo do exercício no WOD real do aluno, com slug genérico 'custom'.
    """
    count = 0
    for day in parsed_payload.get('days', []) or []:
        for block in day.get('blocks', []) or []:
            for movement in block.get('movements', []) or []:
                if not movement.get('movement_slug'):
                    count += 1
    return count


def list_unlinked_projection_movements(projection_preview):
    """List movements without a catalog match or a student-facing reference link."""
    items = []
    if not projection_preview:
        return items

    movements = []
    for entry in projection_preview.get('entries', []) or []:
        if entry.get('status') != 'ready':
            continue
        for block in entry.get('projection_blocks', []) or []:
            movements.extend(block.get('movements', []) or [])
    candidate_slugs = {
        slug
        for movement in movements
        if (slug := (movement.get('movement_slug') or '').strip()) and slug != 'custom'
    }
    catalog_status_by_slug = lookup_movement_catalog_status(candidate_slugs)

    for entry in projection_preview.get('entries', []) or []:
        if entry.get('status') != 'ready':
            continue
        day_label = entry.get('weekday_label') or 'Dia sem identificação'
        for block in entry.get('projection_blocks', []) or []:
            block_title = block.get('title') or block.get('kind') or 'Bloco sem título'
            for movement in block.get('movements', []) or []:
                slug = (movement.get('movement_slug') or '').strip()
                catalog_status = catalog_status_by_slug.get(slug, {}) if slug and slug != 'custom' else {}
                demo_video_url = catalog_status.get('demo_video_url', '')
                has_catalog_match = bool(catalog_status.get('is_registered'))
                if has_catalog_match and demo_video_url:
                    continue
                items.append({
                    'day_label': day_label,
                    'block_title': block_title,
                    'movement_label': movement.get('movement_label_raw') or 'Movimento sem nome',
                    'warning_label': (
                        'Sem cadastro no catálogo: texto personalizado sem compatibilidade validada nem vídeo'
                        if not has_catalog_match else
                        'Cadastrado, mas sem vídeo demonstrativo vinculado'
                    ),
                    'is_custom': not has_catalog_match,
                    'demo_video_url': demo_video_url,
                })
    return items


def _build_projection_week_calendar(projection_preview, parsed_payload):
    if not projection_preview:
        return []
    weekday_titles = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
    week_start = projection_preview.get('target_week_start')
    entries_by_weekday = {weekday: [] for weekday in range(7)}
    for entry in projection_preview.get('entries', []):
        weekday = entry.get('weekday_index')
        if isinstance(weekday, int) and 0 <= weekday <= 6:
            entries_by_weekday[weekday].append(entry)
    planned_weekdays = {
        day.get('weekday')
        for day in (parsed_payload.get('days', []) or [])
        if isinstance(day.get('weekday'), int) and 0 <= day['weekday'] <= 6
    }
    result = []
    for weekday, title in enumerate(weekday_titles):
        entries = entries_by_weekday[weekday]
        canceled_count = projection_preview.get('canceled_by_weekday', {}).get(weekday, 0)
        is_planned = weekday in planned_weekdays
        if entries and all(entry.get('status') == 'ready' for entry in entries) and canceled_count:
            status, status_label = 'attention', 'Destinos prontos · aula(s) cancelada(s)'
        elif entries and all(entry.get('status') == 'ready' for entry in entries):
            status, status_label = 'ready', 'Destinos prontos'
        elif entries:
            status, status_label = 'attention', 'Conferir exceções'
        elif canceled_count:
            status, status_label = 'attention', f'{canceled_count} aula(s) cancelada(s)'
        elif is_planned:
            status, status_label = 'no_sessions', 'Sem aula elegível'
        else:
            status, status_label = 'no_workout', 'Sem treino'
        workout_date = week_start + timedelta(days=weekday) if week_start else None
        result.append({
            'weekday_index': weekday,
            'weekday_label': title,
            'date_iso': workout_date.isoformat() if workout_date else '',
            'date_label': workout_date.strftime('%d/%m') if workout_date else '',
            'is_planned': is_planned,
            'entry_count': len(entries),
            'canceled_count': canceled_count,
            'ready_count': sum(1 for entry in entries if entry.get('status') == 'ready'),
            'status': status,
            'status_label': status_label,
        })
    return result


def _decorate_preview_payload(parsed_payload, *, week_start=None):
    unresolved_items = []
    auto_fixed_items = []
    total_blocks = 0
    total_movements = 0
    first_unresolved_target_id = ''
    for day_index, day in enumerate(parsed_payload.get('days', [])):
        day_has_unresolved = False
        day_unresolved_count = 0
        day_preview_movements = []
        day['day_index'] = day_index
        weekday = day.get('weekday')
        if week_start is not None and isinstance(weekday, int) and 0 <= weekday <= 6:
            workout_date = week_start + timedelta(days=weekday)
            day['date_iso'] = workout_date.isoformat()
            day['date_label'] = workout_date.strftime('%d/%m')
        for block_index, block in enumerate(day.get('blocks', [])):
            total_blocks += 1
            block_unresolved_count = 0
            block['block_index'] = block_index
            block['block_focus_id'] = f'smart-paste-block-{day_index}-{block_index}'
            for movement_index, movement in enumerate(block.get('movements', [])):
                movement['display_label'] = _smart_paste_display_label(movement)
                movement['review_target_id'] = f'review-item-{day_index}-{block_index}-{movement_index}'
                if len(day_preview_movements) < 3:
                    day_preview_movements.append(movement['display_label'])
                total_movements += 1
                if movement.get('llm_resolved'):
                    auto_fixed_items.append(
                        {
                            'day_label': day.get('weekday_label', ''),
                            'block_title': block.get('title') or block.get('kind', ''),
                            'display_label': movement.get('display_label') or movement.get('movement_label_raw', ''),
                            'note': movement.get('llm_fix_note') or '',
                        }
                    )
                if not movement.get('movement_slug'):
                    day_has_unresolved = True
                    day_unresolved_count += 1
                    block_unresolved_count += 1
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
            block['has_unresolved'] = block_unresolved_count > 0
            block['unresolved_count'] = block_unresolved_count
            block['is_clean'] = block_unresolved_count == 0
        day['has_unresolved'] = day_has_unresolved
        day['unresolved_count'] = day_unresolved_count
        day['preview_movements'] = day_preview_movements
    parsed_payload['summary'] = {
        'days_count': len(parsed_payload.get('days', [])),
        'blocks_count': total_blocks,
        'movements_count': total_movements,
        'unresolved_count': len(unresolved_items),
        'unresolved_items': unresolved_items[:8],
        'first_unresolved_target_id': first_unresolved_target_id,
        'current_unresolved_item': unresolved_items[0] if unresolved_items else None,
        'auto_fixed_count': len(auto_fixed_items),
        'auto_fixed_items': auto_fixed_items[:8],
        'parse_errors_count': len(parsed_payload.get('parse_errors') or []),
    }
    return parsed_payload


def _load_wod_generation_credit_summary(today):
    """Le a cota de geracao automatica (Fase 1). Nunca quebra a pagina se a
    migration de WodGenerationCreditLedger ainda nao rodou nesse box."""
    try:
        ledger = get_or_create_current_ledger(today)
    except Exception:
        return None
    return {
        'free_credits_total': ledger.free_credits_total,
        'free_credits_remaining': ledger.free_credits_remaining,
        'purchased_credits_available': ledger.purchased_credits_available,
        'credits_remaining': ledger.credits_remaining,
    }


def load_surface_weekly_wod_plan_for_user(*, user, today):
    if not getattr(user, 'is_authenticated', False):
        return None
    current_week_plan = (
        WeeklyWodPlan.objects.filter(created_by=user, week_start=_default_week_start(today))
        .order_by('-updated_at', '-id')
        .first()
    )
    if current_week_plan:
        return current_week_plan
    # A coach may paste next week's WOD and reopen the page later. Recover the
    # latest unfinished draft so its automatic resolution can resume.
    return (
        WeeklyWodPlan.objects.filter(
            created_by=user,
            status=WeeklyWodPlanStatus.DRAFT,
            week_start__gte=today,
        )
        .order_by('-updated_at', '-id')
        .first()
    )


def _build_page_payload(*, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-smart-paste',
            'title': 'WOD Semana',
            'subtitle': 'Cole a semana, confira a leitura e feche um rascunho organizado.',
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='WOD Semana',
                title='Cole a semana. Nós organizamos os treinos.',
                copy='Revise somente o que precisar. Depois, os WODs entram nas aulas e aguardam aprovação para aparecer aos alunos.',
                aria_label='WOD Semana',
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
            css=[
                'css/design-system/operations.css',
                'css/design-system/operations/workspace/wod-smart-paste.css',
            ],
            js=['js/core/forms.js', 'js/operations/wod_smart_paste.js', 'js/operations/smart_paste_week_monday.js'],
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
    projection_preview_auto_open=None,
    projection_distribution_warning=None,
    auto_open_review_target=None,
):
    week_start = _default_week_start(today)
    max_week = _max_week_start(today)
    weekly_plan = plan or load_surface_weekly_wod_plan_for_user(user=request.user, today=today)
    form = form or WeeklyWodSmartPasteForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'workout_program': getattr(weekly_plan, 'workout_program_id', None),
            'week_start': (getattr(weekly_plan, 'week_start', None) or week_start).strftime('%d/%m/%Y'),
            'label': getattr(weekly_plan, 'label', ''),
            'source_text': getattr(weekly_plan, 'source_text', ''),
        }
    )
    projection_form = projection_form or WeeklyWodProjectionForm(
        initial={
            'plan_id': getattr(weekly_plan, 'id', None),
            'workout_program': getattr(weekly_plan, 'workout_program_id', None),
            'idempotency_key': uuid4(),
            # A semana definida no WOD Semana é a âncora de toda a jornada.
            # Antes, a distribuição usava a próxima segunda sugerida, podendo
            # aplicar o plano em uma semana diferente sem um gesto explícito.
            'target_week_start': (
                getattr(weekly_plan, 'week_start', None) or week_start
            ).strftime('%d/%m/%Y'),
            'class_types': [_class_type_for_program(getattr(weekly_plan, 'workout_program', None))],
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
    parsed_payload = _decorate_preview_payload(
        parsed_payload,
        week_start=getattr(weekly_plan, 'week_start', None),
    )
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
        'workout_programs': WorkoutProgram.objects.filter(is_active=True),
        'selected_workout_program': getattr(weekly_plan, 'workout_program', None),
        'smart_paste_preview': parsed_payload,
        'smart_paste_days': parsed_payload.get('days', []),
        'smart_paste_review_days': [day for day in parsed_payload.get('days', []) if day.get('has_unresolved')],
        'smart_paste_should_auto_retry': bool(
            weekly_plan
            and weekly_plan.status == WeeklyWodPlanStatus.DRAFT
            and parsed_payload.get('summary', {}).get('unresolved_count')
            and not parsed_payload.get('movement_resolution', {}).get('state')
        ),
        'smart_paste_warnings': parsed_payload.get('parse_warnings', []),
        'smart_paste_parse_errors': parsed_payload.get('parse_errors', []),
        'smart_paste_weekly_normalization': parsed_payload.get('weekly_normalization', {}),
        'smart_paste_unlinked_movements': list_unlinked_projection_movements(projection_preview),
        'smart_paste_summary': parsed_payload.get('summary', {}),
        'smart_paste_movement_resolution': parsed_payload.get('movement_resolution', {}),
        'smart_paste_step': 3 if projection_preview else (2 if parsed_payload.get('days') else 1),
        'smart_paste_auto_open_review_target': auto_open_review_target or '',
        'projection_form': projection_form,
        'projection_preview': projection_preview,
        'projection_distribution_warning': projection_distribution_warning,
        'smart_paste_projection_week': _build_projection_week_calendar(
            projection_preview,
            parsed_payload,
        ),
        'projection_preview_auto_open': (
            projection_preview is not None
            if projection_preview_auto_open is None
            else bool(projection_preview_auto_open)
        ),
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
        'smart_paste_picker_min': week_start.strftime('%Y-%m-%d'),
        'smart_paste_picker_max': max_week.strftime('%Y-%m-%d'),
        'smart_paste_picker_value': (
            getattr(weekly_plan, 'week_start', None) or week_start
        ).strftime('%Y-%m-%d'),
        'wod_generation_credit_summary': _load_wod_generation_credit_summary(today),
    }
    attach_page_payload(
        context,
        payload_key='operation_page',
        payload=_build_page_payload(current_role_slug=current_role.slug),
    )
    return context


__all__ = ['build_weekly_wod_smart_paste_context', 'load_surface_weekly_wod_plan_for_user']
