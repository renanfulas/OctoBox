"""
ARQUIVO: Recebedor oficial de Webhooks Financeiros (Segurança Padrão Bancário).

POR QUE ELE EXISTE:
- A Stripe se comunica com o OctoBox de forma assíncrona.
- O sistema não pode confiar em requests HTTP comuns para dar baixa financeira.

O QUE ESTE ARQUIVO FAZ:
1. Autentica a integridade do Webhook usando HMAC (Secret da Stripe).
2. Trava o registro do pagamento atômicamente (Pessimistic Lock / Anti-Duplo Gasto).
3. Atualiza o status financeiro e registra a trilha de auditoria.

PONTOS CRITICOS:
- Se falhar, DEVE retornar status de erro para a Stripe (assim ela faz retentativas automáticas).
"""

import json
import logging
import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone

from auditing import log_audit_event
from finance.models import Payment, PaymentStatus

logger = logging.getLogger(__name__)

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test')
STRIPE_WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'whsec_test')

@csrf_exempt
@require_POST
def stripe_webhook_receiver(request):
    """
    Endpoint Criptograficamente Seguro para Escuta da Stripe.
    """
    payload = request.body
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    
    # 🛡️ Blindagem 1: Assinatura HMAC Webhook (Nunca confie na requisição)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400, content="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature: Hackers sendo rejeitados na borda.
        logger.warning(f"Tentativa de falsificação de webhook financeiro rejeitada. IP: {request.META.get('REMOTE_ADDR')}")
        return HttpResponse(status=400, content="Invalid signature")

    # Filtramos apenas os eventos que importam (quando o dinheiro cai na conta)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        payment_id = session.get('metadata', {}).get('payment_id')
        version_locked = session.get('metadata', {}).get('version_locked')
        
        if not payment_id or version_locked is None:
            logger.error("Webhook recebido sem metadata de roteamento (payment_id / version_locked).")
            return HttpResponse(status=400, content="Missing metadata")

        # 🛡️ Blindagem 2: Atomic Transaction e Pessimistic Lock (Double-Spend Zero)
        try:
            with transaction.atomic():
                # select_for_update tranca a linha no Postgres até o commit terminar.
                # any duplicate webhook processing will wait or fail.
                payment = Payment.objects.select_for_update().get(pk=payment_id)
                
                # Previne que o mesmo evento seja processado duas vezes
                if payment.status == PaymentStatus.PAID:
                    return HttpResponse(status=200, content="Already paid")
                
                # Validação Conservadora: O valor original de fato bate com o Checkout da Stripe?
                if session['amount_total'] != int(payment.amount * 100):
                    logger.error(f"Inconsistência de valores detectada no Payment {payment.id}. Recusando baixa.")
                    return HttpResponse(status=400, content="Amount mismatch")
                
                # Baixa Concluída
                payment.status = PaymentStatus.PAID
                payment.paid_at = timezone.now()
                # Aumentamos a versão para atestar a mudança atômica.
                payment.version += 1
                payment.save(update_fields=['status', 'paid_at', 'version', 'updated_at'])
                
                # 🛡️ Blindagem 3: Trilha Incorruptível
                log_audit_event(
                    actor=None, # Processo de sistema autônomo
                    action="payment_settled_via_stripe",
                    target=payment,
                    description=f"Pagamento processado e blindado via Webhook ID: {event['id']}",
                )

        except Payment.DoesNotExist:
            logger.error(f"Payment {payment_id} não encontrado durante webhook.")
            return HttpResponse(status=404, content="Payment not found")
        except Exception as e:
            logger.error(f"Falha atômica durante liquidação de pagamento: {str(e)}")
            return HttpResponse(status=500, content="Internal failure during resolution")

    # Retorna HTTP 200 pra Stripe parar de emitir o mesmo webhook.
    return HttpResponse(status=200)

__all__ = ['stripe_webhook_receiver']
