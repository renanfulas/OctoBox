"""
ARQUIVO: contexto do hub leve do editor de WOD.

POR QUE ELE EXISTE:
- oferece uma rota canônica curta para entrar no corredor de edicao sem quebrar o editor por aula.

O QUE ESTE ARQUIVO FAZ:
1. monta o payload da pagina de entrada do editor.
2. lista aulas recentes e proximas com link direto para edicao.
3. anexa a navegacao compartilhada do corredor de WOD.
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH
from operations.models import ClassSession, SessionStatus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from .workout_corridor_navigation import build_workout_corridor_tabs


def _build_page_payload(*, page_title, page_subtitle, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-editor-home',
            'title': page_title,
            'subtitle': page_subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Editor',
                title='Escolha a aula e monte o WOD.',
                copy='O corredor do WOD precisa parecer facil: primeiro escolha a aula, depois ajuste o treino e publique sem ruído.',
                actions=[
                    {'label': 'Voltar a operacao', 'href': reverse('role-operations'), 'kind': 'secondary'},
                    {'label': 'Ver historico', 'href': reverse('workout-publication-history'), 'kind': 'ghost'},
                ],
                aria_label='Hub de edicao do WOD',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-editor-home',
            'scope': 'operations-coach',
        },
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )


def build_workout_editor_overview_context(*, request, today, current_role, page_title, page_subtitle):
    window_start = timezone.now() - timedelta(days=1)
    queryset = (
        ClassSession.objects.select_related('coach', 'workout')
        .filter(status__in=(SessionStatus.SCHEDULED, SessionStatus.OPEN, SessionStatus.COMPLETED))
        .filter(scheduled_at__gte=window_start)
        .order_by('scheduled_at')
    )
    if current_role.slug == ROLE_COACH:
        queryset = queryset.filter(coach=request.user)

    editor_sessions = []
    for session in queryset[:12]:
        workout = getattr(session, 'workout', None)
        editor_sessions.append(
            {
                'id': session.id,
                'title': session.title,
                'scheduled_label': timezone.localtime(session.scheduled_at).strftime('%d/%m %H:%M'),
                'coach_label': (
                    (session.coach.get_full_name() or session.coach.username)
                    if session.coach is not None
                    else 'Sem coach'
                ),
                'status_label': workout.get_status_display() if workout is not None else 'Sem WOD',
                'status_tone': (
                    'success'
                    if workout is not None and workout.status == 'published'
                    else 'warning'
                    if workout is not None and workout.status == 'pending_approval'
                    else 'danger'
                    if workout is not None and workout.status == 'rejected'
                    else 'info'
                ),
                'summary': (
                    workout.title
                    if workout is not None and workout.title
                    else 'Abrir a aula para montar ou revisar o treino.'
                ),
                'href': reverse('coach-session-workout-editor', args=[session.id]),
            }
        )

    return {
        'operation_page_payload': _build_page_payload(
            page_title=page_title,
            page_subtitle=page_subtitle,
            current_role_slug=current_role.slug,
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='editor',
            current_role_slug=current_role.slug,
            editor_href=reverse('workout-editor-home'),
        ),
        'editor_sessions': tuple(editor_sessions),
        'editor_sessions_empty_copy': (
            'Nenhuma aula entrou na janela curta de edicao ainda. Assim que uma aula aparecer, ela vira um atalho aqui.'
        ),
    }


__all__ = ['build_workout_editor_overview_context']
