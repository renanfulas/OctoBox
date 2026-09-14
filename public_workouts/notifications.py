"""
ARQUIVO: avisos de cobranca do corredor de treinos (Onda B2 do CORDA, V4).

POR QUE ELE EXISTE:
- copia a FORMA de finance/payment_notifications.py::notify_payment_confirmed
  (D.00) — mesmo desenho de "por canal, nunca propaga, sempre loga" — mas
  chamando os senders proprios do corredor (student_identity/delivery_gateways.py,
  ja usado pelo login por e-mail da Onda B1), nunca editando finance/.

PONTOS CRITICOS:
- Falha de canal e logada e NUNCA propaga — nao pode derrubar o drain
  (mesma regra do box: "nao pode falhar o webhook", aqui "nao pode falhar
  o drain de avisos").
- So e-mail por enquanto: o corredor ainda nao tem push nem WhatsApp
  proprios (essa infraestrutura e do app do aluno de box). Adicionar
  canal aqui e trabalho de outra onda, nao invencao deste modulo.
"""

from __future__ import annotations

import logging

from student_identity.delivery_gateways import StudentEmailDeliveryError, get_student_email_gateway

logger = logging.getLogger(__name__)

_OFFSET_LABELS = {
    -7: 'Seu pagamento vence em 7 dias',
    -3: 'Seu pagamento vence em 3 dias',
    -1: 'Seu pagamento vence amanha',
    0: 'Seu pagamento vence hoje',
    2: 'Seu treino foi pausado por falta de pagamento',
}


def _send_due_email(payment, offset_days: int) -> str:
    account = payment.subscription.account
    if not account or not account.email:
        return 'skipped'

    subject = _OFFSET_LABELS.get(offset_days, 'Aviso de cobranca — Treinos')
    body = (
        f'{subject}.\n\n'
        f'Valor: R$ {payment.gross_amount}\n'
        f'Vencimento: {payment.due_date.isoformat()}\n'
    )
    get_student_email_gateway().send(subject=subject, body=body, to_email=account.email)
    return 'sent'


def notify_payment_due(payment, offset_days: int) -> dict:
    """Dispara o aviso de cobranca ao aluno. Devolve o status por canal.

    Nunca levanta: quem chama (drain_public_workout_notices) decide o que
    fazer com o resultado — sent_at so e gravado se nenhum canal deu erro.
    """
    result = {'email': 'skipped'}

    try:
        result['email'] = _send_due_email(payment, offset_days)
    except StudentEmailDeliveryError:
        logger.exception('notify_payment_due: falha no e-mail. payment=%s offset_days=%s', payment.id, offset_days)
        result['email'] = 'error'
    except Exception:
        logger.exception(
            'notify_payment_due: falha inesperada no e-mail. payment=%s offset_days=%s', payment.id, offset_days
        )
        result['email'] = 'error'

    return result


__all__ = ['notify_payment_due']
