"""
ARQUIVO: definicao do papel DEV.

POR QUE ELE EXISTE:
- Separa manutencao tecnica do poder operacional do negocio.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do papel DEV.
2. Lista capacidades de suporte, manutencao e investigacao.
3. Define permissoes conservadoras para leitura ampla e auditoria.

PONTOS CRITICOS:
- DEV nao deve virar superusuario informal.
- O papel tecnico precisa continuar separado do acesso de negocio e do acesso de contingencia.
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
    'studentidentity': {'view'},
    'studentappinvitation': {'view'},
    'studentinvitationdelivery': {'view'},
    'studentinvitationdeliveryevent': {'view'},
    'studenttransfer': {'view'},
}
