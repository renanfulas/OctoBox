"""
ARQUIVO: confirmacao ao aluno na baixa do pagamento (T5).

POR QUE ELE EXISTE:
- Fechava-se a baixa do pagamento sem nenhum aviso ao aluno (T5 do diagnostico).
  Aqui mora a confirmacao multi-canal disparada na reconciliacao do Stripe.

O QUE ELE FAZ:
- E-mail: envio real (reusa signup.email_sender), quando o aluno tem e-mail.
- WhatsApp: FUNDACAO — o canal ainda nao esta disponivel no OctoBox. Fica atras
  da flag PAYMENT_WHATSAPP_CONFIRMATION_ENABLED (default False); quando ligar,
  implementar o envio real usando student.phone (numero WhatsApp) + o pipeline.

PONTOS CRITICOS:
- Chamado de DENTRO de schema_context(box) pelo router — student e acessivel.
- Falha por canal e logada e NUNCA propaga (nao pode falhar o webhook).
"""

import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings

logger = logging.getLogger(__name__)


def notify_payment_confirmed(payment) -> dict:
    """Dispara a confirmacao da baixa ao aluno. Devolve o status por canal."""
    result = {'email': 'skipped', 'whatsapp': 'skipped'}

    try:
        result['email'] = _send_confirmation_email(payment)
    except Exception:
        logger.exception('notify_payment_confirmed: falha no e-mail. payment=%s', getattr(payment, 'id', None))
        result['email'] = 'error'

    try:
        result['whatsapp'] = _send_confirmation_whatsapp(payment)
    except Exception:
        logger.exception('notify_payment_confirmed: falha no whatsapp. payment=%s', getattr(payment, 'id', None))
        result['whatsapp'] = 'error'

    return result


def _build_confirmation_copy(payment) -> tuple[str, str, str]:
    name = (getattr(payment.student, 'full_name', '') or 'Aluno').strip()
    # payment.amount e Decimal no runtime, mas coagimos defensivamente (em testes
    # / fontes diversas pode chegar como str) antes de formatar.
    try:
        amount_value = Decimal(str(payment.amount))
    except (InvalidOperation, TypeError):
        amount_value = Decimal('0')
    amount = f'{amount_value:.2f}'.replace('.', ',')
    subject = 'Pagamento confirmado — OctoBox'
    text_body = (
        f'Ola {name}, recebemos a confirmacao do seu pagamento de R$ {amount}. '
        f'Obrigado! — OctoBox'
    )
    html_body = (
        f'<p>Ola {name},</p>'
        f'<p>Recebemos a confirmacao do seu pagamento de <strong>R$ {amount}</strong>.</p>'
        f'<p>Obrigado! — OctoBox</p>'
    )
    return subject, text_body, html_body


def _send_confirmation_email(payment) -> str:
    email = (getattr(payment.student, 'email', '') or '').strip()
    if not email:
        return 'skipped'  # aluno sem e-mail cadastrado

    from signup.email_sender import send_html_email

    subject, text_body, html_body = _build_confirmation_copy(payment)
    send_html_email(subject=subject, text_body=text_body, html_body=html_body, to_email=email)
    return 'sent'


def _send_confirmation_whatsapp(payment) -> str:
    """FUNDACAO: WhatsApp ainda nao disponivel. Atras de flag.

    Quando o canal existir: ligar PAYMENT_WHATSAPP_CONFIRMATION_ENABLED e
    implementar o envio real aqui usando payment.student.phone (numero WhatsApp).
    """
    if not getattr(settings, 'PAYMENT_WHATSAPP_CONFIRMATION_ENABLED', False):
        logger.info(
            'payment confirmation whatsapp: desativado (fundacao). payment=%s',
            getattr(payment, 'id', None),
        )
        return 'disabled'

    # TODO(whatsapp): enviar via pipeline real quando o canal estiver disponivel.
    logger.warning(
        'payment confirmation whatsapp habilitado, mas envio ainda nao implementado. payment=%s',
        getattr(payment, 'id', None),
    )
    return 'not_implemented'


__all__ = ['notify_payment_confirmed']
