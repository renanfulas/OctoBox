"""
ARQUIVO: contexto HTTP fino do planner semanal de WOD.

POR QUE ELE EXISTE:
- monta payload de tela sem misturar builder puro com request/template.

O QUE ESTE ARQUIVO FAZ:
1. resolve semana solicitada.
2. carrega sessoes permitidas para o papel atual.
3. monta tabs, hero e contrato de planner.
"""

from datetime import timedelta

from django.db import OperationalError, ProgrammingError
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from .workout_corridor_navigation import build_workout_corridor_tabs
from .models import WorkoutPlannerTemplatePickerEvent
from .workout_planner_builders import build_planner_week, load_planner_sessions, resolve_week_start
from .workout_approval_policy import resolve_workout_approval_policy
from .workout_planner_actions import find_previous_slot_workout
from .workout_templates import build_persisted_workout_template_options


def _build_page_payload(*, page_title, page_subtitle, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-planner',
            'title': page_title,
            'subtitle': page_subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Planner',
                title='Semana de WOD em uma so grade.',
                copy='Planeje, encontre lacunas e abra o editor certo sem depender de uma fila linear.',
                actions=[
                    {'label': 'Aprovacoes', 'href': reverse('workout-approval-board'), 'kind': 'secondary'},
                    {'label': 'Historico', 'href': reverse('workout-publication-history'), 'kind': 'ghost'},
                ],
                aria_label='Planner semanal de WOD',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-planner',
            'scope': 'operations-wod-planner',
        },
        assets=build_page_assets(
            css=[
                'css/design-system/operations.css',
                'css/design-system/operations/workspace/wod-planner.css',
            ],
            deferred_js=['js/operations/wod_planner.js'],
        ),
    )


def _build_planner_template_usage_panel(*, trusted_template_options):
    templates = list(trusted_template_options)
    total_templates = len(templates)
    publish_direct_count = sum(1 for item in templates if item['policy_hint']['label'] == 'Publica direto')
    approval_count = sum(1 for item in templates if item['policy_hint']['label'] == 'Vai para aprovacao')
    cold_count = sum(1 for item in templates if item.get('is_cold'))
    top_templates = tuple(templates[:3])
    return {
        'total_templates': total_templates,
        'publish_direct_count': publish_direct_count,
        'approval_count': approval_count,
        'cold_count': cold_count,
        'top_templates': top_templates,
    }


def _build_planner_template_funnel_panel(*, template_options, days=30):
    cutoff = timezone.now() - timedelta(days=days)

    def _empty_panel():
        return {
            'window_label': f'Ultimos {days} dias',
            'opened_count': 0,
            'selected_count': 0,
            'applied_count': 0,
            'completed_count': 0,
            'published_count': 0,
            'pending_count': 0,
            'opened_to_selected_label': '0%',
            'selected_to_applied_label': '0%',
            'applied_to_completed_label': '0%',
            'completed_to_published_label': '0%',
            'top_templates': (),
        }

    try:
        queryset = WorkoutPlannerTemplatePickerEvent.objects.filter(created_at__gte=cutoff)
        counts_by_event = {
            row['event_name']: row['count']
            for row in queryset.values('event_name').annotate(count=Count('id'))
        }
        opened_count = counts_by_event.get('opened', 0)
        selected_count = counts_by_event.get('selected', 0)
        applied_count = counts_by_event.get('applied', 0)
        completed_count = counts_by_event.get('completed', 0)
        published_count = queryset.filter(event_name='completed', action_outcome='published').count()
        pending_count = queryset.filter(event_name='completed', action_outcome='pending_approval').count()

        template_rows = []
        for option in template_options:
            template_id = option['id']
            template_events = queryset.filter(template_id=template_id)
            selected_events = template_events.filter(event_name='selected').count()
            applied_events = template_events.filter(event_name='applied').count()
            completed_events = template_events.filter(event_name='completed').count()
            published_events = template_events.filter(event_name='completed', action_outcome='published').count()
            template_rows.append(
                {
                    'id': template_id,
                    'label': option['label'],
                    'usage_count': option['usage_count'],
                    'selected_count': selected_events,
                    'applied_count': applied_events,
                    'completed_count': completed_events,
                    'published_count': published_events,
                    'conversion_label': f'{published_events}/{selected_events or 1} publicacoes',
                    'policy_hint': option['policy_hint'],
                }
            )
    except (OperationalError, ProgrammingError):
        return _empty_panel()

    top_templates = sorted(
        template_rows,
        key=lambda item: (
            item['published_count'],
            item['completed_count'],
            item['selected_count'],
            item['usage_count'],
            item['label'],
        ),
        reverse=True,
    )[:3]

    def _rate(numerator, denominator):
        if not denominator:
            return '0%'
        return f'{round((numerator / denominator) * 100):.0f}%'

    return {
        'window_label': f'Ultimos {days} dias',
        'opened_count': opened_count,
        'selected_count': selected_count,
        'applied_count': applied_count,
        'completed_count': completed_count,
        'published_count': published_count,
        'pending_count': pending_count,
        'opened_to_selected_label': _rate(selected_count, opened_count),
        'selected_to_applied_label': _rate(applied_count, selected_count),
        'applied_to_completed_label': _rate(completed_count, applied_count),
        'completed_to_published_label': _rate(published_count, completed_count),
        'top_templates': tuple(top_templates),
    }


def build_workout_planner_context(*, request, current_role, page_title, page_subtitle):
    week_start = resolve_week_start(request.GET.get('week'))
    sessions = load_planner_sessions(
        week_start=week_start,
        current_role_slug=current_role.slug,
        actor=request.user,
    )
    previous_slot_source_map = {session.id: find_previous_slot_workout(session=session) for session in sessions}
    current_policy = resolve_workout_approval_policy(actor=request.user)
    trusted_template_options = []
    for option in build_persisted_workout_template_options(
        current_role_slug=current_role.slug,
        actor=request.user,
    ):
        if not option.get('is_trusted'):
            continue
        if current_policy == 'trusted_template':
            policy_hint = {
                'label': 'Publica direto',
                'detail': 'Pela politica atual, este template confiavel tende a publicar direto.',
                'tone': 'success',
            }
        elif current_policy == 'coach_autonomy' and getattr(request.user, 'is_trusted_author', False):
            policy_hint = {
                'label': 'Publica direto',
                'detail': 'A politica atual libera publicacao direta para este ator confiavel.',
                'tone': 'success',
            }
        else:
            policy_hint = {
                'label': 'Vai para aprovacao',
                'detail': 'Pela politica atual, esta aplicacao ainda cai na fila de aprovacao.',
                'tone': 'warning',
            }
        trusted_template_options.append({**option, 'policy_hint': policy_hint})
    trusted_template_options = tuple(trusted_template_options)
    template_usage_panel = _build_planner_template_usage_panel(trusted_template_options=trusted_template_options[:5])
    template_funnel_panel = _build_planner_template_funnel_panel(
        template_options=trusted_template_options[:5],
    )
    planner_week = build_planner_week(
        week_start=week_start,
        sessions=sessions,
        previous_slot_source_map=previous_slot_source_map,
        current_role_slug=current_role.slug,
        trusted_template_options=trusted_template_options[:5],
    )
    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    return {
        'operation_page_payload': _build_page_payload(
            page_title=page_title,
            page_subtitle=page_subtitle,
            current_role_slug=current_role.slug,
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='planner',
            current_role_slug=current_role.slug,
            editor_href=reverse('workout-planner'),
        ),
        'planner_week': planner_week,
        'planner_previous_week_href': f"{reverse('workout-planner')}?week={previous_week.isoformat()}",
        'planner_next_week_href': f"{reverse('workout-planner')}?week={next_week.isoformat()}",
        'planner_today_href': reverse('workout-planner'),
        'planner_trusted_template_options': trusted_template_options[:5],
        'planner_template_usage_panel': template_usage_panel,
        'planner_template_funnel_panel': template_funnel_panel,
    }


__all__ = ['build_workout_planner_context']
