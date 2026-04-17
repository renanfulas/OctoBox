from __future__ import annotations

from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def build_student_invitation_operations_page(
    *,
    current_box_slug: str,
    recent_invites: list[dict],
    stalled_invites: list[dict],
    pending_memberships: list[dict],
    managed_memberships: list[dict],
    observability_cards: list[dict],
    observability_alerts: list[str],
):
    return build_page_payload(
        context={
            'page_key': 'student-app-invitations',
            'title': 'Convites do app do aluno',
            'subtitle': 'Gere links seguros de ativacao sem misturar staff e aluno.',
        },
        data={
            'hero': build_page_hero(
                eyebrow='Aluno App',
                title='Convites operacionais prontos.',
                copy='A equipe gera um link por aluno, com validade curta e uma porta so para o box atual.',
                actions=[
                    {'label': 'Voltar para configuracoes', 'href': '/configuracoes-operacionais/', 'kind': 'secondary'},
                ],
                aria_label='Convites operacionais do app do aluno',
                classes=['system-map-hero'],
                data_panel='student-app-invitations-hero',
            ),
            'box_root_slug': current_box_slug,
            'guardrails': [
                'Cada convite nasce para um aluno e um box raiz so.',
                'Convite individual libera o aluno ao fechar a identidade; convite do box pede aprovacao depois.',
                'Um novo convite fecha a janela do convite anterior ainda aberto para o mesmo aluno.',
                'O link nao entrega acesso sozinho; ele ainda precisa fechar com a identidade social do aluno.',
            ],
            'observability_cards': observability_cards,
            'observability_alerts': observability_alerts,
            'stalled_invites': stalled_invites,
            'pending_memberships': pending_memberships,
            'managed_memberships': managed_memberships,
            'recent_invites': recent_invites,
        },
        assets=build_page_assets(
            css=[
                'css/guide/system-map.css',
                'css/student_identity/operations_invites.css',
            ],
        ),
    )
