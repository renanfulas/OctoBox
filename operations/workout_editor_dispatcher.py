"""
ARQUIVO: dispatcher de intents do editor de WOD do coach.

POR QUE ELE EXISTE:
- remove da view o roteamento das intents de POST sem mudar o comportamento do editor.

O QUE ESTE ARQUIVO FAZ:
1. mapeia intents do editor para handlers.
2. resolve erros de intent desconhecida.
3. delega a execucao para o corredor de actions.

PONTOS CRITICOS:
- manter o contrato de intents estavel para nao quebrar formularios do editor.
- nao virar lugar de regra de negocio; aqui so mora roteamento.
"""

from django.contrib import messages
from django.shortcuts import redirect


def get_coach_workout_editor_intent_handler(view, intent: str):
    intent_handlers = {
        'save_workout': view._handle_save_workout,
        'add_block': view._handle_add_block,
        'delete_block': view._handle_delete_block,
        'update_block': view._handle_update_block,
        'add_movement': view._handle_add_movement,
        'delete_movement': view._handle_delete_movement,
        'update_movement': view._handle_update_movement,
        'submit_for_approval': view._handle_submit_for_approval,
        'duplicate_workout': view._handle_duplicate_workout,
        'apply_quick_template': view._handle_apply_quick_template,
        'apply_stored_template': view._handle_apply_stored_template,
        'create_stored_template': view._handle_create_stored_template,
        'apply_smartplan_paste': view._handle_apply_smartplan_paste,
    }
    return intent_handlers.get(intent)


def dispatch_coach_workout_editor_intent(view, request):
    intent = request.POST.get('intent')
    handler = get_coach_workout_editor_intent_handler(view, intent)
    if handler is None:
        messages.error(request, 'Acao de WOD nao reconhecida neste fluxo.')
        return redirect('coach-session-workout-editor', session_id=view.session.id)
    return handler(request)


__all__ = [
    'dispatch_coach_workout_editor_intent',
    'get_coach_workout_editor_intent_handler',
]
