"""
ARQUIVO: politica pura de sincronizacao comercial de matricula.

POR QUE ELE EXISTE:
- Retira do adapter Django as decisoes de movimento comercial e os textos de negocio da matricula.

O QUE ESTE ARQUIVO FAZ:
1. Classifica a mudanca comercial entre plano atual e plano selecionado.
2. Define o movimento resultante da sincronizacao de matricula.
3. Centraliza os textos comerciais usados no fechamento e abertura de matriculas.

PONTOS CRITICOS:
- Esta politica precisa continuar pura para ser reutilizada por qualquer entrypoint.
"""

from dataclasses import dataclass


def describe_plan_change(*, previous_price, selected_price):
    if selected_price > previous_price:
        return 'upgrade'
    if selected_price < previous_price:
        return 'downgrade'
    return 'troca de plano'


def append_enrollment_note(existing_note: str | None, extra_note: str) -> str:
    current_note = (existing_note or '').strip()
    return '\n'.join(filter(None, [current_note, extra_note]))


@dataclass(frozen=True, slots=True)
class EnrollmentSyncDecision:
    movement: str
    current_enrollment_closing_note: str | None
    new_enrollment_note: str | None
    payment_note: str | None


def build_enrollment_sync_decision(*, has_current_enrollment: bool, same_plan: bool, previous_price=None, selected_price=None) -> EnrollmentSyncDecision:
    if not has_current_enrollment:
        return EnrollmentSyncDecision(
            movement='created',
            current_enrollment_closing_note=None,
            new_enrollment_note='Plano conectado pela tela leve do aluno.',
            payment_note='Primeira cobranca criada no fluxo leve do aluno.',
        )

    if same_plan:
        return EnrollmentSyncDecision(
            movement='status_adjusted',
            current_enrollment_closing_note=None,
            new_enrollment_note=None,
            payment_note='Primeira cobranca criada no fluxo leve do aluno.',
        )

    movement = describe_plan_change(previous_price=previous_price, selected_price=selected_price)
    return EnrollmentSyncDecision(
        movement=movement,
        current_enrollment_closing_note=f'Encerrada por {movement} na tela leve do aluno.',
        new_enrollment_note=f'{movement.capitalize()} aplicada pela tela leve do aluno.',
        payment_note=f'Cobranca criada apos {movement} de plano.',
    )


__all__ = [
    'EnrollmentSyncDecision',
    'append_enrollment_note',
    'build_enrollment_sync_decision',
    'describe_plan_change',
]