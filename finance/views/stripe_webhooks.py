"""
ARQUIVO: receptor HTTP de webhooks da Stripe.

POR QUE ELE EXISTE:
- Ponto de entrada HTTP para eventos assíncronos da Stripe.
- Responsabilidade única: autenticar, persistir o envelope, despachar ao router.

O QUE ESTE ARQUIVO FAZ:
1. Verifica a assinatura HMAC via integrations/stripe/auth.py (sem import stripe aqui).
2. Cria PaymentWebhookEvent com idempotência por event_id.
3. Chama o router da Signal Mesh — toda lógica de negócio fica fora desta view.
4. Retorna 200 para a Stripe parar de reenviar.

PONTOS CRITICOS:
- Nenhuma regra de negócio aqui.
- Retornar 200 em duplicatas — o use case é idempotente.
- Retornar 400 apenas para payload inválido ou assinatura inválida.
"""

import logging

from django.db import IntegrityError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from integrations.stripe.auth import StripeWebhookAuthError, verify_stripe_webhook
from integrations.stripe.models import PaymentWebhookEvent
from integrations.stripe.router import route_payment_webhook_event

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook_receiver(request):
    sig_header = request.headers.get('Stripe-Signature', '')

    try:
        event = verify_stripe_webhook(request.body, sig_header)
    except StripeWebhookAuthError as exc:
        logger.warning('Webhook Stripe rejeitado: %s. IP=%s', exc, request.META.get('REMOTE_ADDR'))
        return HttpResponse(status=400, content=str(exc))

    try:
        webhook_event = PaymentWebhookEvent.objects.create(
            event_id=event['id'],
            event_type=event['type'],
            payload=event,
        )
    except IntegrityError:
        return HttpResponse(status=200, content='Duplicate event')

    route_payment_webhook_event(webhook_event)
    return HttpResponse(status=200)


__all__ = ['stripe_webhook_receiver']
