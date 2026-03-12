"""
ARQUIVO: definicao do papel Coach.

POR QUE ELE EXISTE:
- Isola o escopo tecnico do coach moderador.

O QUE ESTE ARQUIVO FAZ:
1. Define identidade do Coach.
2. Lista capacidades ligadas a aula, presenca e observacao.
3. Define permissoes limitadas ao acompanhamento tecnico.

PONTOS CRITICOS:
- Mudancas aqui influenciam o que o coach pode editar sem invadir o financeiro.
"""

from .base import RoleDefinition

ROLE_COACH = 'Coach'

COACH_ROLE = RoleDefinition(
    slug=ROLE_COACH,
    label='Coach',
    summary='Moderador técnico da rotina de treino e acompanhamento dos alunos.',
    capabilities=(
        'Visualizar turmas, alunos vinculados e presença do dia.',
        'Registrar check-in, falta, observações e ocorrências técnicas.',
        'Acompanhar sinais de queda de frequência e necessidades do aluno.',
    ),
)

COACH_PERMISSIONS = {
    'student': {'view'},
    'classsession': {'view', 'change'},
    'attendance': {'add', 'change', 'view'},
    'behaviornote': {'add', 'change', 'view'},
    'enrollment': {'view'},
    'whatsappcontact': {'view'},
}
