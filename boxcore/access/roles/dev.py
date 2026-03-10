"""
ARQUIVO: definição do papel DEV.

POR QUE ELE EXISTE:
- Separa manutenção técnica do poder operacional do negócio.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do papel DEV.
2. Lista capacidades de suporte, manutenção e investigação.
3. Define permissões conservadoras para leitura ampla e auditoria.

PONTOS CRITICOS:
- DEV não deve virar superusuário informal.
- O papel técnico precisa continuar separado do acesso de negócio e do acesso de contingência.
"""

from .base import RoleDefinition

ROLE_DEV = 'DEV'

DEV_ROLE = RoleDefinition(
    slug=ROLE_DEV,
    label='DEV',
    summary='Perfil técnico para manutenção, leitura sistêmica, suporte e auditoria.',
    capabilities=(
        'Investigar fluxo, navegação, papéis e comportamento do sistema.',
        'Consultar dados operacionais sem assumir rotina de manager ou coach.',
        'Acompanhar trilha de auditoria e apoiar manutenção técnica controlada.',
    ),
)

DEV_PERMISSIONS = {
    'student': {'view'},
    'studentintake': {'view'},
    'membershipplan': {'view'},
    'enrollment': {'view'},
    'classsession': {'view'},
    'attendance': {'view'},
    'payment': {'view'},
    'behaviornote': {'view'},
    'whatsappcontact': {'view'},
    'whatsappmessagelog': {'view'},
    'auditevent': {'view'},
}