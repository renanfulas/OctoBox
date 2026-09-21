"""
ARQUIVO: registro de "motivo de falha OAuth do aluno -> mensagem humana".

POR QUE ELE EXISTE:
- Onda 5 (docs/plans/student-login-magic-link-bugs-corda.md): extrai o mapeamento que
  vivia preso como metodo privado de StudentSignInView (views.py) pra uma funcao de
  modulo reutilizavel, sem mudar o tipo de retorno (continua string simples) — quem
  ja chama isso esperando string (oauth_actions.py:91) nao quebra.

PONTOS CRITICOS:
- NAO confundir com StudentInvitationOperationsView._map_failure_reason (staff_views.py),
  que e um registro DIFERENTE (motivos de falha ao criar convite pelo staff, nao de
  autenticacao OAuth do aluno) — mesmo nome de metodo, dominios diferentes.
"""

from __future__ import annotations


_FAILURE_REASON_COPY = {
    'invite-not-found': 'O convite informado não foi encontrado ou expirou. Tente entrar sem convite.',
    'invite-box-mismatch': 'Este convite não pertence ao box atual.',
    'invite-expired': 'O convite informado não foi encontrado ou expirou. Tente entrar sem convite.',
    'invite-email-mismatch': 'O e-mail informado não corresponde ao convite.',
    'student-email-ambiguous': 'Não foi possível validar este aluno por e-mail neste box.',
    'box-root-mismatch': 'Esta conta de aluno pertence a outro box.',
    'student-box-mismatch': 'Este aluno já está vinculado a outro box.',
    'provider-subject-required': 'Não foi possível validar a identidade social informada.',
    # Onda 3:
    'email-conflict': 'Esse e-mail já tem cadastro neste box. Tente entrar em vez de se cadastrar de novo.',
    'provider-subject-conflict': 'Essa conta já tem acesso em outro box. Peça pro seu box atual gerar um convite novo.',
}

_DEFAULT_FAILURE_COPY = 'Não foi possível autorizar este aluno no box atual.'


def map_student_oauth_failure_reason(reason: str) -> str:
    """Devolve a mensagem humana pro `failure_reason` de autenticação OAuth do aluno."""
    return _FAILURE_REASON_COPY.get(reason, _DEFAULT_FAILURE_COPY)


__all__ = ['map_student_oauth_failure_reason']
