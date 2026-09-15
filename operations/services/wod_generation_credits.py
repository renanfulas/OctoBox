"""
ARQUIVO: cota mensal de geracao automatica de treino via Haiku ("Monte um treino pra mim").

POR QUE ELE EXISTE:
- Fase 1 do plano de geracao automatica: a cota (2 gratis/mes por box) precisa existir
  e ser confiavel ANTES do botao de geracao (Fase 3) chamar o Haiku de verdade.
- consumo por box (nao por coach): qualquer coach da box compartilha a mesma cota.

O QUE ESTE ARQUIVO FAZ:
1. get_or_create_current_ledger(): garante que existe uma linha pro mes corrente
   (reset automatico — mes novo, linha nova com free_credits_used=0).
2. consume_wod_generation_credit(): gasta 1 credito (gratis primeiro, depois comprado)
   de forma atomica. Retorna False sem gastar nada se a cota ja zerou.
3. add_purchased_credits(): credita cota comprada (usado pelo webhook Stripe da Fase 2,
   ainda nao implementada — funcao ja existe pra nao exigir migration nova depois).

PONTOS CRITICOS:
- select_for_update() dentro de transaction.atomic evita credito duplo se dois cliques
  quase simultaneos chegarem ao mesmo tempo (linha travada durante o gasto).
- "periodo" = mes calendario do box (schema atual). Nao ha job de reset: a query
  get_or_create ja cria a linha nova quando o mes vira.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from student_app.models import WodGenerationCreditLedger

FREE_CREDITS_PER_MONTH = 2


def _period_start(today=None):
    today = today or timezone.localdate()
    return today.replace(day=1)


def get_or_create_current_ledger(today=None) -> WodGenerationCreditLedger:
    """Garante e retorna a linha de cota do mes corrente (cria com reset se for mes novo)."""
    ledger, _ = WodGenerationCreditLedger.objects.get_or_create(
        period_start=_period_start(today),
        defaults={'free_credits_total': FREE_CREDITS_PER_MONTH},
    )
    return ledger


@transaction.atomic
def consume_wod_generation_credit(today=None) -> bool:
    """Tenta gastar 1 credito (gratis primeiro, depois comprado).

    Retorna True se conseguiu gastar, False se a cota do mes ja zerou — nesse caso
    nada e alterado (view deve mostrar upsell, nao chamar o Haiku).
    """
    period_start = _period_start(today)
    ledger, _ = WodGenerationCreditLedger.objects.select_for_update().get_or_create(
        period_start=period_start,
        defaults={'free_credits_total': FREE_CREDITS_PER_MONTH},
    )
    if ledger.free_credits_used < ledger.free_credits_total:
        ledger.free_credits_used += 1
        ledger.save(update_fields=['free_credits_used', 'updated_at'])
        return True
    if ledger.purchased_credits_available > 0:
        ledger.purchased_credits_available -= 1
        ledger.save(update_fields=['purchased_credits_available', 'updated_at'])
        return True
    return False


@transaction.atomic
def add_purchased_credits(amount: int, *, today=None) -> WodGenerationCreditLedger:
    """Credita cota comprada no mes corrente. Usado pelo webhook de pagamento (Fase 2)."""
    if amount <= 0:
        raise ValueError('amount deve ser positivo.')
    period_start = _period_start(today)
    ledger, _ = WodGenerationCreditLedger.objects.select_for_update().get_or_create(
        period_start=period_start,
        defaults={'free_credits_total': FREE_CREDITS_PER_MONTH},
    )
    ledger.purchased_credits_available += amount
    ledger.save(update_fields=['purchased_credits_available', 'updated_at'])
    return ledger


__all__ = [
    'FREE_CREDITS_PER_MONTH',
    'get_or_create_current_ledger',
    'consume_wod_generation_credit',
    'add_purchased_credits',
]
