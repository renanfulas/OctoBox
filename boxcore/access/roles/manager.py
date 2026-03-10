"""
ARQUIVO: definição do papel Manager.

POR QUE ELE EXISTE:
- Isola o escopo operacional do gerente.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do Manager.
2. Lista as capacidades administrativas do papel.
3. Define permissões iniciais sobre alunos, agenda e financeiro.

PONTOS CRITICOS:
- Mudanças aqui afetam a fronteira entre gestão e operação técnica.
"""

from .base import RoleDefinition

ROLE_MANAGER = 'Manager'

MANAGER_ROLE = RoleDefinition(
    slug=ROLE_MANAGER,
    label='Manager',
    summary='Gerente focado em operação diária, financeiro, alunos e acompanhamento.',
    capabilities=(
        'Gerenciar alunos, planos, matrículas, pagamentos e ocorrências.',
        'Operar agenda, confirmar presença e tratar faltas e inadimplência.',
        'Acompanhar indicadores operacionais e preparar ações de retenção.',
    ),
)

MANAGER_PERMISSIONS = {
    'student': {'add', 'change', 'view'},
    'studentintake': {'add', 'change', 'view'},
    'membershipplan': {'add', 'change', 'view'},
    'enrollment': {'add', 'change', 'view'},
    'classsession': {'add', 'change', 'view'},
    'attendance': {'add', 'change', 'view'},
    'payment': {'add', 'change', 'view'},
    'behaviornote': {'add', 'change', 'view'},
    'whatsappcontact': {'add', 'change', 'view'},
    'whatsappmessagelog': {'view'},
}