"""
ARQUIVO: fachada publica da Central de Intake.

POR QUE ELE EXISTE:
- Cria um ponto estavel para triagem, atribuicao e decisao de conversao sem espalhar regra pela view ou template.

O QUE ESTE ARQUIVO FAZ:
1. Monta a leitura operacional de cada item da fila.
2. Executa acoes de intake com validacao de papel e transicao simples de estado.
3. Explicita quando um intake deve ser tratado como lead aberto ou conversao pronta.

PONTOS CRITICOS:
- Essa fronteira define o comportamento do modulo de onboarding; se ficar frouxa, a tela vira so mais um espelho do ORM.
"""

from dataclasses import asdict, dataclass

from access.roles import ROLE_MANAGER, ROLE_OWNER, get_user_role
from onboarding.domain import (
    build_intake_conversion_decision,
    build_intake_semantic_state,
    resolve_intake_action_permissions,
)
from onboarding.models import IntakeStatus, StudentIntake


@dataclass(frozen=True, slots=True)
class IntakeQueueActionResult:
    intake_id: int
    status: str
    assigned_to_id: int | None
    message: str


def build_intake_queue_item(*, intake: StudentIntake, actor_role_slug: str) -> dict:
    semantic_state = build_intake_semantic_state(
        status=intake.status,
        linked_student_id=getattr(intake.linked_student, 'id', None),
    )
    conversion = build_intake_conversion_decision(
        status=intake.status,
        linked_student_id=getattr(intake.linked_student, 'id', None),
    )
    action_permissions = resolve_intake_action_permissions(
        status=intake.status,
        linked_student_id=getattr(intake.linked_student, 'id', None),
        is_manager_scope=actor_role_slug in (ROLE_OWNER, ROLE_MANAGER),
    )
    return {
        'object': intake,
        'semantic_state': asdict(semantic_state),
        'conversion': asdict(conversion),
        'action_permissions': action_permissions,
    }


def run_intake_queue_action(*, actor, intake_id: int, action: str) -> IntakeQueueActionResult:
    intake = StudentIntake.objects.select_for_update().select_related('linked_student', 'assigned_to').get(pk=intake_id)
    actor_id = getattr(actor, 'id', None)
    actor_role_slug = getattr(get_user_role(actor), 'slug', '')

    permissions = resolve_intake_action_permissions(
        status=intake.status,
        linked_student_id=getattr(intake.linked_student, 'id', None),
        is_manager_scope=actor_role_slug in (ROLE_OWNER, ROLE_MANAGER),
    )

    if action == 'assign-to-me':
        if not permissions['can_assign_to_me']:
            raise ValueError('Este intake nao pode mais ser assumido nesta etapa.')
        intake.assigned_to = actor
        update_fields = ['assigned_to', 'updated_at']
        message = f'{intake.full_name} agora esta com voce.'
    elif action == 'clear-assignee':
        if not permissions['can_clear_assignee']:
            raise ValueError('So owner ou manager podem remover o responsavel atual deste intake.')
        intake.assigned_to = None
        update_fields = ['assigned_to', 'updated_at']
        message = f'Responsavel removido de {intake.full_name}.'
    elif action == 'start-review':
        if not permissions['can_start_review']:
            raise ValueError('Este intake nao esta mais no ponto de entrar em revisao.')
        intake.status = IntakeStatus.REVIEWING
        if intake.assigned_to_id is None and actor_id is not None:
            intake.assigned_to = actor
            update_fields = ['status', 'assigned_to', 'updated_at']
        else:
            update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} entrou em revisao.'
    elif action == 'mark-matched':
        if not permissions['can_mark_matched']:
            raise ValueError('Este intake nao pode ser marcado como pronto para conversao agora.')
        intake.status = IntakeStatus.MATCHED
        if intake.assigned_to_id is None and actor_id is not None:
            intake.assigned_to = actor
            update_fields = ['status', 'assigned_to', 'updated_at']
        else:
            update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} foi marcado como pronto para conversao.'
    elif action == 'approve-intake':
        if not permissions['can_approve']:
            raise ValueError('Este intake ainda nao pode ser aprovado por esta tela.')
        intake.status = IntakeStatus.APPROVED
        update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} foi aprovado e saiu da fila ativa.'
    elif action == 'reject-intake':
        if not permissions['can_reject']:
            raise ValueError('Este intake nao pode ser rejeitado por esta tela.')
        intake.status = IntakeStatus.REJECTED
        update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} foi rejeitado e saiu da fila ativa.'
    else:
        raise ValueError('Acao de intake desconhecida para esta central.')

    intake.save(update_fields=update_fields)
    return IntakeQueueActionResult(
        intake_id=intake.id,
        status=intake.status,
        assigned_to_id=intake.assigned_to_id,
        message=message,
    )


__all__ = [
    'IntakeQueueActionResult',
    'build_intake_queue_item',
    'run_intake_queue_action',
]