from __future__ import annotations

from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


def build_student_invitation_operations_page(*, current_box_slug: str, recent_invites: list[dict], stalled_invites: list[dict]):
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
                'Um novo convite fecha a janela do convite anterior ainda aberto para o mesmo aluno.',
                'O link nao entrega acesso sozinho; ele ainda precisa fechar com a identidade social do aluno.',
            ],
            'stalled_invites': stalled_invites,
            'recent_invites': recent_invites,
        },
        assets=build_page_assets(
            css=[
                'css/guide/system-map.css',
                'css/student_identity/operations_invites.css',
            ],
        ),
    )
