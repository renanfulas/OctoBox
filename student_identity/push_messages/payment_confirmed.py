"""
ARQUIVO: builder de payload para push de pagamento confirmado.

POR QUE ELE EXISTE:
- mesma separacao de push_messages/session_cancelled.py: compor a mensagem
  (copy, limites de caracteres, deep link) fora da logica de entrega.
- mantem a copy consistente com o e-mail de confirmacao
  (finance/payment_notifications.py::_build_confirmation_copy).

PONTOS CRITICOS:
- titulo <= 30 chars, corpo <= 90 chars (mesmos limites de session_cancelled.py).
- tag = 'payment-confirmed-{payment_id}' garante dedupe nativo do browser.
- url aponta para /aluno/configuracoes/ (nao para o botao "Pagar", que so
  existe via POST — a fatura ja aparece paga na tela de configuracoes).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.urls import reverse

TITLE_MAX_CHARS = 30
BODY_MAX_CHARS = 90


@dataclass(frozen=True, slots=True)
class PushPayload:
    title: str
    body: str
    url: str
    tag: str
    require_interaction: bool = False


def build_payment_confirmed_payload(*, payment_id: int, amount) -> PushPayload:
    """
    Compoe o payload de push para pagamento confirmado.

    Argumentos:
        payment_id — pk do Payment (para tag).
        amount     — valor pago (Decimal, str ou o que payment.amount trouxer).
    """
    try:
        amount_value = Decimal(str(amount))
    except (InvalidOperation, TypeError):
        amount_value = Decimal('0')
    amount_label = f'{amount_value:.2f}'.replace('.', ',')

    title = 'Pagamento confirmado'
    body = f'Recebemos seu pagamento de R$ {amount_label}. Obrigado!'
    tag = f'payment-confirmed-{payment_id}'
    url = reverse('student-app-settings')

    # Truncagem defensiva — nunca quebrar entrega por copy longo.
    title = title[:TITLE_MAX_CHARS]
    body = body[:BODY_MAX_CHARS]

    return PushPayload(title=title, body=body, url=url, tag=tag, require_interaction=False)


__all__ = ['PushPayload', 'build_payment_confirmed_payload']
