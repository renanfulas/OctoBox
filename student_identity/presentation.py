from __future__ import annotations

from access.admin import admin_changelist_url
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def build_student_invitation_operations_page(
    *,
    current_box_slug: str,
    access_matrix: dict,
    recent_invites: list[dict],
    stalled_invites: list[dict],
    pending_memberships: list[dict],
    managed_memberships: list[dict],
    observability_cards: list[dict],
    observability_alerts: list[str],
    journey_funnels: list[dict],
    priority_of_day: dict | None,
    recommended_queue: list[dict],
    active_box_invite_link: dict | None,
):
    return build_page_payload(
        context={
            'page_key': 'student-app-invitations',
            'title': 'Central de ativacao do aluno',
            'subtitle': 'Ative alunos no app com o corredor certo e sem atrito para a operacao.',
        },
        data={
            'hero': build_page_hero(
                eyebrow='Aluno App',
                title='Central de ativacao pronta para uso.',
                copy='Aqui a recepcao e o owner escolhem o melhor caminho para colocar o aluno dentro do app sem confusao.',
                actions=[
                    {'label': 'Voltar para configuracoes', 'href': '/configuracoes-operacionais/', 'kind': 'secondary'},
                ],
                aria_label='Convites operacionais do app do aluno',
                classes=['system-map-hero'],
                data_panel='student-app-invitations-hero',
                actions_slot='student-app-invitations-hero-actions',
            ),
            'box_root_slug': current_box_slug,
            'access_matrix': access_matrix,
            'guardrails': [
                'Cada convite vale para um aluno ou um box por vez.',
                'Quando voce gera um novo convite para o mesmo aluno, o anterior deixa de ser o principal.',
                'Link de grupo ajuda a puxar a massa; convite individual ajuda a recuperar caso a caso.',
                'O aluno ainda precisa entrar com Google ou Apple para o acesso nascer de verdade.',
            ],
            'active_box_invite_link': active_box_invite_link,
            'admin_invites_href': admin_changelist_url('student_identity', 'studentappinvitation'),
            'observability_cards': observability_cards,
            'observability_alerts': observability_alerts,
            'journey_funnels': journey_funnels,
            'priority_of_day': priority_of_day,
            'recommended_queue': recommended_queue,
            'stalled_invites': stalled_invites,
            'pending_memberships': pending_memberships,
            'managed_memberships': managed_memberships,
            'recent_invites': recent_invites,
        },
        assets=build_page_assets(
            css=[
                'css/design-system/operations.css',
                'css/guide/system-map.css',
                'css/student_identity/operations_invites.css',
            ],
        ),
    )
