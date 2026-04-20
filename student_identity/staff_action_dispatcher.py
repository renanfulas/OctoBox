"""
ARQUIVO: dispatcher de actions da central operacional de ativacao do aluno.

POR QUE ELE EXISTE:
- tira de `student_identity/staff_views.py` o roteamento de intents do POST.
"""


def get_student_invitation_post_action_handler(view, action: str):
    action_handlers = {
        'create-box-link': view._handle_create_box_link,
        'pause-box-link': view._handle_pause_box_link,
        'send-email': view._handle_send_email,
        'open-whatsapp': view._handle_open_whatsapp,
        'approve-membership': view._handle_approve_membership,
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
    return handler(request)
