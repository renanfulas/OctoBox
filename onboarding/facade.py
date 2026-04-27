"""
ARQUIVO: fachada publica da Central de Intake.

POR QUE ELE EXISTE:
- Cria um ponto estavel para triagem, atribuicao e decisao de conversao sem espalhar regra pela view ou template.

O QUE ESTE ARQUIVO FAZ:
1. Monta a leitura operacional de cada item da fila.
2. Executa acoes de intake com validacao de papel e transicao simples de estado.
3. Explicita quando um intake deve ser tratado como em conversa, resolvido ou convertido.

PONTOS CRITICOS:
- Essa fronteira define o comportamento do modulo de onboarding; se ficar frouxa, a tela vira so mais um espelho do ORM.
"""

from dataclasses import asdict, dataclass

from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_OWNER, get_user_role
from onboarding.domain import (
    build_intake_conversion_decision,
    build_intake_semantic_state,
    resolve_intake_action_permissions,
)
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from shared_support.whatsapp_links import build_whatsapp_message_href


@dataclass(frozen=True, slots=True)
class IntakeQueueActionResult:
    intake_id: int
    status: str
    assigned_to_id: int | None
    message: str


def _build_intake_whatsapp_message(*, intake: StudentIntake) -> str:
    first_name = str(getattr(intake, 'full_name', '') or '').strip().split(' ')[0] or 'oi'
    return (
        f'Oi, {first_name}! Vi seu interesse no OctoBox e queria te ajudar a dar o proximo passo. '
        'Se fizer sentido, ja podemos organizar sua entrada como aluno.'
    )


def _get_registration_age_days(*, intake: StudentIntake, today=None) -> int:
    reference_day = today or timezone.localdate()
    created_day = timezone.localtime(intake.created_at).date() if timezone.is_aware(intake.created_at) else intake.created_at.date()
    return max((reference_day - created_day).days, 0)


def _build_registration_age_label(*, intake: StudentIntake, today=None) -> str:
    elapsed_days = _get_registration_age_days(intake=intake, today=today)
    if elapsed_days == 0:
        return 'Hoje'
    if elapsed_days == 1:
        return 'Há 1 dia'
    return f'Há {elapsed_days} dias'


def build_intake_queue_item(*, intake: StudentIntake, actor_role_slug: str, today=None) -> dict:
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
        'can_send_whatsapp_invite': intake.source == IntakeSource.IMPORT and bool(intake.phone),
        'registration_age_days': _get_registration_age_days(intake=intake, today=today),
        'registration_age_label': _build_registration_age_label(intake=intake, today=today),
        'whatsapp_href': build_whatsapp_message_href(
            phone=intake.phone,
            message=_build_intake_whatsapp_message(intake=intake),
        ),
    }


def run_intake_queue_action(*, actor, intake_id: int, action: str) -> IntakeQueueActionResult:
    intake = StudentIntake.objects.select_for_update().select_related('linked_student', 'assigned_to').get(pk=intake_id)
    actor_role_slug = getattr(get_user_role(actor), 'slug', '')

    permissions = resolve_intake_action_permissions(
        status=intake.status,
        linked_student_id=getattr(intake.linked_student, 'id', None),
        is_manager_scope=actor_role_slug in (ROLE_OWNER, ROLE_MANAGER),
    )

    if action == 'move-to-conversation':
        if intake.status != IntakeStatus.NEW:
            raise ValueError('So leads novos podem ser movidos para Em conversa por esta tela.')
        intake.status = IntakeStatus.REVIEWING
        update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} foi movido para Em conversa.'
    elif action == 'reject-intake':
        if not permissions['can_reject']:
            raise ValueError('Esta entrada nao pode ser rejeitada por esta tela.')
        intake.status = IntakeStatus.REJECTED
        update_fields = ['status', 'updated_at']
        message = f'{intake.full_name} foi rejeitado e saiu da fila ativa.'
    else:
        raise ValueError('Acao de entradas desconhecida para esta central.')

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
