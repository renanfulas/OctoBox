"""
ARQUIVO: contexto da tela minima de gestao de templates de WOD.
"""

from django.urls import reverse

from operations.forms import WorkoutApprovalPolicyForm, WorkoutTemplateManagementFilterForm, WorkoutTemplateMetadataForm
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from .workout_corridor_navigation import build_workout_corridor_tabs
from .workout_approval_policy import get_or_create_workout_approval_policy_setting
from .workout_templates import build_manageable_workout_templates, build_workout_template_management_summary


def build_workout_template_management_context(*, request, current_role, page_title, page_subtitle):
    active_only = request.GET.get('active') == '1'
    featured_only = request.GET.get('featured') == '1'
    query = (request.GET.get('q') or '').strip()
    approval_policy_setting = get_or_create_workout_approval_policy_setting(actor=request.user)
    return {
        'operation_page_payload': build_page_payload(
            context={
                'page_key': 'operations-workout-template-management',
                'title': page_title,
                'subtitle': page_subtitle,
                'mode': 'workspace',
                'role_slug': current_role.slug,
            },
            data={
                'hero': build_page_hero(
                    eyebrow='Templates',
                    title='Templates persistentes de WOD.',
                    copy='Veja o que esta ativo, o que ja foi usado e ajuste a disponibilidade sem abrir um fluxo pesado.',
                    actions=[{'label': 'Voltar ao planner', 'href': reverse('workout-planner'), 'kind': 'secondary'}],
                    aria_label='Gestao de templates persistentes de WOD',
                    classes=['coach-hero'],
                    data_panel='coach-hero',
                    actions_slot='coach-hero-actions',
                ),
            },
            behavior={
                'surface_key': 'operations-workout-template-management',
                'scope': 'operations-coach',
            },
            assets=build_page_assets(css=['css/design-system/operations.css']),
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='planner',
            current_role_slug=current_role.slug,
            editor_href=reverse('workout-planner'),
        ),
        'stored_templates': build_manageable_workout_templates(
            current_role_slug=current_role.slug,
            actor=request.user,
            active_only=active_only,
            featured_only=featured_only,
            query=query,
        ),
        'template_management_summary': build_workout_template_management_summary(
            current_role_slug=current_role.slug,
            actor=request.user,
        ),
        'template_filter_state': {'active_only': active_only, 'featured_only': featured_only, 'query': query},
        'template_filter_form': WorkoutTemplateManagementFilterForm(initial={'q': query, 'active': active_only, 'featured': featured_only}),
        'template_metadata_form': WorkoutTemplateMetadataForm(),
        'approval_policy_setting': approval_policy_setting,
        'approval_policy_form': WorkoutApprovalPolicyForm(initial={'approval_policy': getattr(approval_policy_setting, 'approval_policy', 'strict')}),
    }


__all__ = ['build_workout_template_management_context']
