"""
ARQUIVO: templates de convite do app do aluno.

POR QUE ELE EXISTE:
- centraliza a copy operacional do convite sem espalhar texto em view ou template.
"""

from __future__ import annotations


def build_student_invitation_subject(*, box_name: str) -> str:
    return f'Seu acesso ao app do aluno do {box_name}'


def build_student_invitation_email_body(*, student_name: str, invite_url: str, box_name: str, expires_label: str) -> str:
    first_name = (student_name or 'aluno').split()[0]
    return (
        f'Oi, {first_name}.\n\n'
        f'Seu acesso ao app do aluno do {box_name} esta pronto.\n'
        f'Use este link para ativar a sua conta:\n{invite_url}\n\n'
        f'Este convite fica valido ate {expires_label}.\n'
        'Depois disso, se precisar, o box pode gerar um novo convite para voce.\n\n'
        'Importante: o acesso final ainda depende da confirmacao da sua identidade social no app.\n'
    )


def build_student_invitation_whatsapp_body(*, student_name: str, invite_url: str, box_name: str, expires_label: str) -> str:
    first_name = (student_name or 'aluno').split()[0]
    return (
        f'Oi, {first_name}! Seu acesso ao app do aluno do {box_name} esta pronto. '
        f'Ative por este link: {invite_url} '
        f'Este convite fica valido ate {expires_label}.'
    )


__all__ = [
    'build_student_invitation_email_body',
    'build_student_invitation_subject',
    'build_student_invitation_whatsapp_body',
]
