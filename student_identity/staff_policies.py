"""
ARQUIVO: policies da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- separa regras por papel da view monolitica de operacao do app do aluno.

O QUE ESTE ARQUIVO FAZ:
1. resolve o papel efetivo do ator.
2. monta a matriz de acesso da superficie operacional.
3. aplica gates curtos de permissao para acoes sensiveis.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect

from access.roles import ROLE_COACH, get_user_role


def get_student_operations_actor_role_slug(user) -> str:
    return getattr(get_user_role(user), 'slug', '')


def build_student_operations_access_matrix(
    *,
    role_slug: str,
    invite_operator_roles: tuple[str, ...],
    membership_approval_roles: tuple[str, ...],
    membership_lifecycle_roles: tuple[str, ...],
) -> dict:
    is_read_only_identity_observer = role_slug == ROLE_COACH
    return {
        'role_slug': role_slug,
        'can_operate_invites': role_slug in invite_operator_roles,
        'can_approve_membership': role_slug in membership_approval_roles,
        'can_manage_membership_lifecycle': role_slug in membership_lifecycle_roles,
        'can_change_email': role_slug in invite_operator_roles,
        'can_view_sensitive_identity_data': not is_read_only_identity_observer,
        'can_view_invite_links': not is_read_only_identity_observer,
        'is_read_only_identity_observer': is_read_only_identity_observer,
    }


def actor_has_student_operations_capability(access_matrix: dict) -> bool:
    return (
        access_matrix['can_operate_invites']
        or access_matrix['can_approve_membership']
        or access_matrix['can_manage_membership_lifecycle']
    )


def deny_read_only_student_operations_actor(request):
    messages.error(
        request,
        'Coach acompanha o estado do app do aluno em modo leitura. Convite, aprovacao e governanca de identidade ficam com Recepcao, Manager, Owner ou DEV.',
    )
    return redirect('student-invitation-operations')


def require_student_operations_action_role(
    request,
    *,
    actor_role_slug: str,
    allowed_roles: tuple[str, ...],
    denied_message: str,
):
    if actor_role_slug not in allowed_roles:
        messages.error(request, denied_message)
        return redirect('student-invitation-operations')
    return None
