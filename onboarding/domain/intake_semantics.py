"""
ARQUIVO: regras de dominio da fila de intake.

POR QUE ELE EXISTE:
- Separa o registro tecnico de intake da leitura comercial de lead e da prontidao para conversao.

O QUE ESTE ARQUIVO FAZ:
1. Classifica o intake em estagios semanticos.
2. Decide quando a conversao para aluno deve ser liberada.
3. Resolve quais acoes operacionais fazem sentido para cada caso.

PONTOS CRITICOS:
- A semantica daqui orienta o que o operador enxerga como lead, triagem ou conversao pronta.
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


def build_intake_semantic_state(*, status: str, linked_student_id: int | None) -> IntakeSemanticState:
    if linked_student_id is not None or status in (IntakeStatus.APPROVED, IntakeStatus.REJECTED):
        return IntakeSemanticState(
            entity_label='Intake',
            semantic_stage='resolved',
            semantic_label='Resolvido',
            note='A entrada ja saiu da fila ativa e nao representa lead operacional aberto.',
        )

    if status == IntakeStatus.MATCHED:
        return IntakeSemanticState(
            entity_label='Intake',
            semantic_stage='conversion-ready',
            semantic_label='Conversao pronta',
            note='O caso ja passou da triagem e esta maduro para abrir a ficha definitiva.',
        )

    return IntakeSemanticState(
        entity_label='Intake',
        semantic_stage='lead-open',
        semantic_label='Lead aberto',
        note='O registro segue como entrada em triagem e ainda pede leitura comercial ou operacional.',
    )


def build_intake_conversion_decision(*, status: str, linked_student_id: int | None) -> IntakeConversionDecision:
    if linked_student_id is not None:
        return IntakeConversionDecision(
            can_convert=False,
            reason='Este intake ja esta ligado a um aluno definitivo.',
            action_label='Ja convertido',
        )

    if status == IntakeStatus.NEW:
        return IntakeConversionDecision(
            can_convert=False,
            reason='Comece a triagem ou marque o caso como pronto para conversao antes de abrir a ficha.',
            action_label='Triar antes de converter',
        )

    if status in (IntakeStatus.REVIEWING, IntakeStatus.MATCHED, IntakeStatus.APPROVED):
        return IntakeConversionDecision(
            can_convert=True,
            reason='A triagem atual ja sustenta abrir a ficha definitiva sem depender de leitura paralela.',
            action_label='Converter em aluno',
        )

    return IntakeConversionDecision(
        can_convert=False,
        reason='Casos rejeitados nao devem abrir conversao direta para aluno.',
        action_label='Conversao bloqueada',
    )


def resolve_intake_action_permissions(*, status: str, linked_student_id: int | None, is_manager_scope: bool) -> dict[str, bool]:
    is_resolved = linked_student_id is not None or status in (IntakeStatus.APPROVED, IntakeStatus.REJECTED)
    return {
        'can_assign_to_me': not is_resolved,
        'can_clear_assignee': is_manager_scope and not is_resolved,
        'can_start_review': not is_resolved and status == IntakeStatus.NEW,
        'can_mark_matched': not is_resolved and status in (IntakeStatus.NEW, IntakeStatus.REVIEWING),
        'can_approve': is_manager_scope and not is_resolved and status in (IntakeStatus.REVIEWING, IntakeStatus.MATCHED),
        'can_reject': is_manager_scope and not is_resolved,
    }


__all__ = [
    'IntakeConversionDecision',
    'IntakeSemanticState',
    'build_intake_conversion_decision',
    'build_intake_semantic_state',
    'resolve_intake_action_permissions',
]