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
from decimal import Decimal
from datetime import date


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


@dataclass(frozen=True, slots=True)
class ProrataCreditDecision:
    credit_amount: Decimal
    new_charge_amount: Decimal
    needs_manager_review: bool
    note: str


def calculate_prorata_credit(*, previous_price: Decimal, selected_price: Decimal, period_start_date: date, today: date, billing_cycle_days: int = 30) -> ProrataCreditDecision:
    # 1. Dias passados (limitados a no máximo billing_cycle_days caso esteja atrasado mas de alguma forma rodando pro-rata)
    days_used = min(max((today - period_start_date).days, 0), billing_cycle_days)
    
    # 2. Custo diário do plano antigo
    daily_cost = previous_price / Decimal(billing_cycle_days)
    
    # 3. Valor já utilizado (consumido) e o que sobra (crédito real)
    value_used = daily_cost * Decimal(days_used)
    credit_amount = max(previous_price - value_used, Decimal('0.00'))

    # 4. Abater do novo plano
    new_charge_amount = selected_price - credit_amount
    needs_manager_review = False
    
    note_lines = [
        f"Cancel & Replace (Padrão Stripe):",
        f"- Valor antigo: R$ {previous_price:.2f}",
        f"- Período utilizado: {days_used}/{billing_cycle_days} dias",
        f"- Crédito obtido: R$ {credit_amount:.2f}",
        f"- Novo valor (com abate): R$ {max(new_charge_amount, Decimal('0.00')):.2f}"
    ]
    
    if new_charge_amount < 0:
        new_charge_amount = Decimal('0.00')
        needs_manager_review = True
        note_lines.append(f"⚠️ Atenção (Downgrade): Gerou saldo credor para o cliente. Valor zerado e pendente de revisão gerencial.")

    return ProrataCreditDecision(
        credit_amount=credit_amount.quantize(Decimal('0.01')),
        new_charge_amount=new_charge_amount.quantize(Decimal('0.01')),
        needs_manager_review=needs_manager_review,
        note='\n'.join(note_lines),
    )


__all__ = [
    'EnrollmentSyncDecision',
    'ProrataCreditDecision',
    'append_enrollment_note',
    'build_enrollment_sync_decision',
    'calculate_prorata_credit',
    'describe_plan_change',
]