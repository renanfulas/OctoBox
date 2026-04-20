"""
ARQUIVO: policy do callback OAuth do app do aluno.

POR QUE ELE EXISTE:
- separa da view a leitura e validacao do payload que volta do provedor social.

O QUE ESTE ARQUIVO FAZ:
1. le o erro retornado pelo provedor.
2. valida state e provider do callback.
3. garante a presenca do authorization code.
4. entrega um payload canonico para a action do callback.

PONTOS CRITICOS:
- state invalido ou code ausente precisam continuar falhando com a mesma mensagem.
- este corredor nao deve disparar side effects; ele apenas valida a entrada.
"""

from __future__ import annotations

from dataclasses import dataclass

from .oauth_state import read_oauth_state


class StudentOAuthCallbackPolicyError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StudentOAuthCallbackInput:
    code: str
    state_payload: dict

    @property
    def invite_token(self) -> str:
        return (self.state_payload.get('invite_token') or '').strip()


def read_student_oauth_callback_input(*, request, provider: str) -> StudentOAuthCallbackInput:
    error = request.GET.get('error') or request.POST.get('error')
    if error:
        raise StudentOAuthCallbackPolicyError('O provedor cancelou ou recusou a autenticacao.')

    state_payload = read_oauth_state(request.GET.get('state') or request.POST.get('state') or '')
    if state_payload is None or state_payload.get('provider') != provider:
        raise StudentOAuthCallbackPolicyError('O estado da autenticacao nao e valido. Tente novamente.')

    code = (request.GET.get('code') or request.POST.get('code') or '').strip()
    if not code:
        raise StudentOAuthCallbackPolicyError('O provedor nao retornou um codigo de autenticacao valido.')

    return StudentOAuthCallbackInput(code=code, state_payload=state_payload)


__all__ = [
    'StudentOAuthCallbackInput',
    'StudentOAuthCallbackPolicyError',
    'read_student_oauth_callback_input',
]
