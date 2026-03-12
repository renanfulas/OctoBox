"""
ARQUIVO: definicao do papel Owner.

POR QUE ELE EXISTE:
- Isola o que pertence ao dono da academia.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do Owner.
2. Define capacidades estrategicas do papel.
3. Define permissoes de acesso total ao dominio principal.

PONTOS CRITICOS:
- Mudancas nas permissoes daqui alteram o alcance mais alto do sistema.
"""

from .base import RoleDefinition

ROLE_OWNER = 'Owner'

OWNER_ROLE = RoleDefinition(
    slug=ROLE_OWNER,
    label='Owner',
    summary='Dono da academia com visão completa de operação, receita e estratégia.',
    capabilities=(
        'Acesso total ao sistema e ao painel administrativo.',
        'Visualização global de financeiro, retenção, agenda e performance do box.',
        'Gestão de usuários, papéis, regras e futuras integrações.',
    ),
)

OWNER_PERMISSIONS = {
    'student': {'add', 'change', 'delete', 'view'},
    'studentintake': {'add', 'change', 'delete', 'view'},
    'membershipplan': {'add', 'change', 'delete', 'view'},
    'enrollment': {'add', 'change', 'delete', 'view'},
    'classsession': {'add', 'change', 'delete', 'view'},
    'attendance': {'add', 'change', 'delete', 'view'},
    'payment': {'add', 'change', 'delete', 'view'},
    'behaviornote': {'add', 'change', 'delete', 'view'},
    'whatsappcontact': {'add', 'change', 'delete', 'view'},
    'whatsappmessagelog': {'add', 'change', 'delete', 'view'},
}
