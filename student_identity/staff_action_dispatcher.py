"""
ARQUIVO: dispatcher de actions da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- tira de `student_identity/staff_views.py` o roteamento de intents do POST.

PONTOS CRITICOS:
- Onda 0 (docs/plans/student-login-magic-link-bugs-corda.md): nenhuma das 11 actions tinha
  rede de seguranca — uma excecao nao tratada em qualquer handler subia crua ate o 500 global
  do Django. O try/except abaixo loga so metadados estruturados (nunca request.POST cru, que
  pode conter e-mail/telefone/senha) e devolve uma tela amigavel em vez do crash.
"""

import logging

from django.contrib import messages
from django.shortcuts import redirect

from shared_support.box_runtime import get_box_runtime_slug

logger = logging.getLogger(__name__)


def get_student_invitation_post_action_handler(view, action: str):
    action_handlers = {
        'create-box-link': view._handle_create_box_link,
        'pause-box-link': view._handle_pause_box_link,
        'send-email': view._handle_send_email,
        'open-whatsapp': view._handle_open_whatsapp,
        'approve-membership': view._handle_approve_membership,
        'clear-membership': view._handle_clear_membership,
        'change-email': view._handle_change_email,
        'suspend-membership': view._handle_suspend_membership,
        'reactivate-membership': view._handle_reactivate_membership,
        'revoke-membership': view._handle_revoke_membership,
        'create-invite': view._handle_create_invite,
    }
    return action_handlers.get(action, view._handle_create_invite)


def dispatch_student_invitation_post_action(view, request):
    action = request.POST.get('action', 'create-invite').strip()
    handler = get_student_invitation_post_action_handler(view, action)
    try:
        return handler(request)
    except Exception:
        logger.exception(
            'student_invitation_operations_action_failed action=%s actor_id=%s box_root_slug=%s',
            action,
            getattr(request.user, 'id', None),
            get_box_runtime_slug(),
        )
        messages.error(
            request,
            'Não conseguimos concluir essa ação agora. Tente de novo em instantes; '
            'se continuar acontecendo, avise o suporte.',
        )
        return redirect('student-invitation-operations')
