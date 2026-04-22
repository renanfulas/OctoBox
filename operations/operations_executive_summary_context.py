"""
ARQUIVO: contexto do resumo executivo operacional.

POR QUE ELE EXISTE:
- move a leitura macro para uma superficie transversal e reduz o peso cognitivo da aprovacao.

O QUE ESTE ARQUIVO FAZ:
1. monta o payload do resumo executivo.
2. deriva uma versao curta para coach.
3. reaproveita agregados do historico publicado sem levar formulários para a tela macro.
"""

from django.urls import reverse

from access.roles import ROLE_COACH
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from .workout_corridor_navigation import build_workout_corridor_tabs
from .workout_published_history import build_published_workout_history


def _build_page_payload(*, page_title, page_subtitle, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-executive-summary',
            'title': page_title,
            'subtitle': page_subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Resumo executivo',
                title='Leitura transversal do corredor de WOD.',
                copy='Este painel junta sinais macro sem roubar o foco da operação. Pense nele como a varanda do prédio: dá para ver o conjunto sem misturar com o trabalho do chão.',
                actions=[
                    {'label': 'Abrir historico', 'href': reverse('workout-publication-history'), 'kind': 'secondary'},
                ],
                aria_label='Resumo executivo operacional',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-executive-summary',
            'scope': 'operations-owner',
        },
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )


def build_operations_executive_summary_context(*, current_role, page_title, page_subtitle):
    published_history = build_published_workout_history(limit=18, current_role_slug=current_role.slug)
    assist = published_history['assist']
    coach_minimal_cards = (
        {
            'label': 'WODs acompanhados',
            'value': assist['total'],
            'tone': 'info',
            'copy': 'Janela curta das publicacoes recentes que merecem leitura.',
        },
        {
            'label': 'Pendencias reais',
            'value': assist['live_follow_up_count'],
            'tone': 'warning',
            'copy': 'Casos com alerta vivo ou retorno ainda pedindo acao.',
        },
        {
            'label': 'Alertas criticos',
            'value': assist['critical_alert_count'],
            'tone': 'danger',
            'copy': 'Sinais fortes que pedem resposta antes de virarem ruido recorrente.',
        },
    )
    return {
        'operation_page_payload': _build_page_payload(
            page_title=page_title,
            page_subtitle=page_subtitle,
            current_role_slug=current_role.slug,
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='summary',
            current_role_slug=current_role.slug,
        ),
        'published_history': published_history,
        'executive_summary_mode': 'coach-minimal' if current_role.slug == ROLE_COACH else 'full',
        'coach_minimal_cards': coach_minimal_cards,
    }


__all__ = ['build_operations_executive_summary_context']
