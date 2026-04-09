"""
ARQUIVO: regras de dominio da fila de intake.

POR QUE ELE EXISTE:
- Separa o registro tecnico de intake da leitura comercial de em conversa e da decisao de conversao.

O QUE ESTE ARQUIVO FAZ:
1. Classifica o intake em estagios semanticos.
2. Decide quando a conversao para aluno deve ser liberada.
3. Resolve quais acoes operacionais fazem sentido para cada caso.

PONTOS CRITICOS:
- A semantica daqui orienta o que o operador enxerga como em conversa, resolvido ou caso ja convertido.
"""

from dataclasses import dataclass

from onboarding.models import IntakeStatus


@dataclass(frozen=True, slots=True)
class IntakeSemanticState:
    entity_label: str
    semantic_stage: str
    semantic_label: str
    note: str


@dataclass(frozen=True, slots=True)
class IntakeConversionDecision:
    can_convert: bool
    reason: str
    action_label: str
    action_type: str


def build_intake_semantic_state(*, status: str, linked_student_id: int | None) -> IntakeSemanticState:
    if linked_student_id is not None or status in (IntakeStatus.APPROVED, IntakeStatus.REJECTED):
        return IntakeSemanticState(
            entity_label='Entrada',
            semantic_stage='resolved',
            semantic_label='Resolvido',
            note='A entrada ja saiu da fila ativa e nao representa mais uma conversa comercial em andamento.',
        )

    if status == IntakeStatus.NEW:
        return IntakeSemanticState(
            entity_label='Entrada',
            semantic_stage='new-leads',
            semantic_label='Lead',
            note='O registro acabou de entrar na fila e ainda pede primeiro contato da equipe.',
        )

    return IntakeSemanticState(
        entity_label='Entrada',
        semantic_stage='lead-open',
        semantic_label='Lead aberto',
        note='O registro segue quente na fila comercial e pode virar aluno assim que a conversa fechar.',
    )


def build_intake_conversion_decision(*, status: str, linked_student_id: int | None) -> IntakeConversionDecision:
    if linked_student_id is not None:
        return IntakeConversionDecision(
            can_convert=False,
            reason='Esta entrada ja esta ligada a um aluno definitivo.',
            action_label='Ja convertido',
            action_type='none',
        )

    if status == IntakeStatus.NEW:
        return IntakeConversionDecision(
            can_convert=True,
            reason='Quando o lead responder ou mostrar interesse real, mova para Em conversa com um clique.',
            action_label='Em conversa',
            action_type='move-to-conversation',
        )

    if status in (IntakeStatus.REVIEWING, IntakeStatus.MATCHED):
        return IntakeConversionDecision(
            can_convert=True,
            reason='Se a conversa ja fechou, voce pode abrir a ficha definitiva direto daqui.',
            action_label='Converter em aluno',
            action_type='convert-student',
        )

    return IntakeConversionDecision(
        can_convert=False,
        reason='Casos rejeitados nao devem abrir conversao direta para aluno.',
        action_label='Conversao bloqueada',
        action_type='none',
    )


def resolve_intake_action_permissions(*, status: str, linked_student_id: int | None, is_manager_scope: bool) -> dict[str, bool]:
    is_resolved = linked_student_id is not None or status in (IntakeStatus.APPROVED, IntakeStatus.REJECTED)
    return {
        'can_reject': not is_resolved,
    }


__all__ = [
    'IntakeConversionDecision',
    'IntakeSemanticState',
    'build_intake_conversion_decision',
    'build_intake_semantic_state',
    'resolve_intake_action_permissions',
]
