"""
ARQUIVO: builders de page payload para workspaces operacionais.

POR QUE ELE EXISTE:
- unifica o contrato de operations com o mesmo shape usado no restante do front.
- mantem a view HTTP curta e previsivel mesmo quando a tela ainda consome aliases legados.
"""

from access.shell_actions import build_shell_action_buttons
from shared_support.page_payloads import build_page_assets, build_page_payload


def build_operation_workspace_page(*, page_key, title, subtitle, scope, snapshot, current_role_slug, focus_key, capabilities=None):
    focus = snapshot.get(focus_key) or []
    return build_page_payload(
        context={
            'page_key': page_key,
            'title': title,
            'subtitle': subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons(
                priority=focus[0] if len(focus) > 0 else None,
                pending=focus[1] if len(focus) > 1 else None,
                next_action=focus[2] if len(focus) > 2 else None,
                scope=scope,
            ),
        },
        data=snapshot,
        capabilities=capabilities or {},
        assets=build_page_assets(css=['css/design-system/operations.css']),
    )