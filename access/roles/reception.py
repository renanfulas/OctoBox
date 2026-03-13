"""
ARQUIVO: definicao do papel Recepcao.

POR QUE ELE EXISTE:
- Isola o escopo de balcao sem empurrar a Recepcao para o manager completo.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do papel Recepcao.
2. Lista capacidades focadas em atendimento, aluno, grade em leitura e cobranca curta.
3. Declara as permissoes minimas para sustentar o MVP funcional.

PONTOS CRITICOS:
- Recepcao nao pode herdar o centro financeiro completo.
- O papel precisa conseguir cadastrar aluno e registrar pagamento curto sem virar gerencia ampla.
"""

from .base import RoleDefinition

ROLE_RECEPTION = 'Recepcao'

RECEPTION_ROLE = RoleDefinition(
    slug=ROLE_RECEPTION,
    label='Recepcao',
    summary='Perfil de balcao para orientar chegada, localizar aluno, ler a grade e resolver cobranca curta.',
    capabilities=(
        'Localizar, cadastrar e atualizar aluno no contexto de atendimento rapido.',
        'Ler a grade de aulas sem ganhar gestao administrativa da agenda.',
        'Resolver cobranca curta e confirmar pagamento sem abrir o financeiro completo.',
    ),
)

RECEPTION_PERMISSIONS = {
    'student': {'add', 'change', 'view'},
    'studentintake': {'view'},
    'membershipplan': {'view'},
    'enrollment': {'add', 'change', 'view'},
    'classsession': {'view'},
    'attendance': {'view'},
    'payment': {'add', 'change', 'view'},
    'whatsappcontact': {'view'},
}