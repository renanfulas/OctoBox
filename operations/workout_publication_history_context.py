"""
ARQUIVO: contexto da pagina de historico operacional do WOD.

POR QUE ELE EXISTE:
- separa o pos-publicacao da tela de aprovacao sem mudar o corredor de dados ja existente.

O QUE ESTE ARQUIVO FAZ:
1. monta o payload da pagina de historico.
2. prepara filtros curtos do historico publicado.
3. expõe follow-up, checkpoint e leitura publicada fora da board de aprovacao.
"""

from django.urls import reverse

from access.roles import ROLE_MANAGER, ROLE_OWNER
from operations.forms import WorkoutApprovalFilterForm, WorkoutWeeklyCheckpointForm
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from .workout_board_builders import build_alerts_context, build_checkpoint_context, build_published_wods_context
from .workout_corridor_navigation import build_workout_corridor_tabs
from .workout_approval_board_context import _build_coach_options


def _build_page_payload(*, page_title, page_subtitle, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-publication-history',
            'title': page_title,
            'subtitle': page_subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Historico',
                title='WOD publicado e leitura pos-publicacao.',
                copy='Aqui a equipe acompanha o que foi ao ar, registra retorno e entende onde o treino ainda pede acao humana.',
                actions=[
                    {'label': 'Voltar a operacao', 'href': reverse('role-operations'), 'kind': 'secondary'},
                ],
                aria_label='Historico operacional do WOD',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-publication-history',
            'scope': 'operations-approval',
        },
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )


def build_workout_publication_history_context(*, request, today, current_role, page_title, page_subtitle):
    filter_form = WorkoutApprovalFilterForm(request.GET or None)
    selected_coach = ''
    today_only = False
    published_reason = ''
    if filter_form.is_valid():
        selected_coach = (filter_form.cleaned_data.get('coach') or '').strip()
        today_only = bool(filter_form.cleaned_data.get('today_only'))
        published_reason = (filter_form.cleaned_data.get('published_reason') or '').strip()
    published_context = build_published_wods_context(
        coach_username=selected_coach,
        today_only=today_only,
        published_reason=published_reason,
        current_role_slug=current_role.slug,
    )
    checkpoint_context = build_checkpoint_context(today=today)
    alerts_context = build_alerts_context(
        coach_username=selected_coach,
        today_only=today_only,
        published_reason=published_reason,
        current_role_slug=current_role.slug,
        published_history=published_context['published_history'],
    )
    weekly_checkpoint_initial = checkpoint_context['weekly_checkpoint_form_initial']
    return {
        'operation_page_payload': _build_page_payload(
            page_title=page_title,
            page_subtitle=page_subtitle,
            current_role_slug=current_role.slug,
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='history',
            current_role_slug=current_role.slug,
        ),
        'approval_filter_form': filter_form,
        'history_filter_state': {
            'coach': selected_coach,
            'today_only': today_only,
            'published_reason': published_reason,
        },
        'approval_coach_options': _build_coach_options(),
        'weekly_checkpoint_form': WorkoutWeeklyCheckpointForm(
            initial=weekly_checkpoint_initial
        ),
        **checkpoint_context,
        **alerts_context,
        'can_manage_weekly_checkpoint': current_role.slug in {ROLE_MANAGER, ROLE_OWNER},
        'current_surface_path': request.get_full_path(),
    }


__all__ = ['build_workout_publication_history_context']
