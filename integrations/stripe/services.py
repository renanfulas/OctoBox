"""
ARQUIVO: Gateway de pagamento com a Stripe (Camada de Segurança).

POR QUE ELE EXISTE:
- Isolar a API da Stripe do resto do OctoBox.
- Implementar as diretrizes de Prevenção de Fraude (Anti-Double-Spend) e Idempotência.

O QUE ESTE ARQUIVO FAZ:
1. Gera Links de Checkout (Payment Intents).
2. Força 'Idempotency-Key' para evitar cobranças simultâneas ou reexecuções de rede.
3. Não confia em valores do front-end (Zero-Trust). Valores vêm 100% da query no banco.

PONTOS CRITICOS:
- Se falhar na geração da sessão, o erro DEVE ser verboso o suficiente para a recepção entender.
"""
import stripe
from django.conf import settings
from django.urls import reverse
from auditing import log_audit_event
from finance.models import Payment

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_placeholder')

def generate_idempotency_key(payment: Payment, action: str) -> str:
    """Gera uma chave determinística para evitar duplo gasto de rede na mesma versão do boleto."""
    return f"octobox_{action}_pay_{payment.id}_v{payment.version}"

def create_checkout_session(payment: Payment, request) -> str:
    """
    Cria a URL de checkout hospedada pela Stripe.
    Segurança Atingida:
    - Zero-Trust: O preço é calculado pelo backend `int(payment.amount * 100)`.
    - Idempotência: Se o usuário clicar 'Pagar' 5x, a Stripe retorna a mesma sessão.
    """
    if payment.status == 'paid':
        raise ValueError("Pagamento já consta como PAGO no banco de dados.")

    # A chave de idempotência atrela o ID do pagamento e a versão de trava otimista (optimistic lock).
    idem_key = generate_idempotency_key(payment, 'checkout')
    
    # Montamos os metadados blindados para o Webhook validar depois:
    metadata = {
        'payment_id': payment.id,
        'student_id': payment.student.id,
        'version_locked': payment.version,
    }

    product_name = "Fatura Avulsa"
    if payment.enrollment and payment.enrollment.plan:
        product_name = f"Plano {payment.enrollment.plan.name} - {payment.installment_number}/{payment.installment_total}"

    success_url = request.build_absolute_uri(reverse('finance:checkout_success', args=[payment.id])) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri(reverse('finance:checkout_cancel', args=[payment.id]))

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'pix'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': product_name,
                        'description': payment.notes or f"Cobrança para {payment.student.full_name}",
                    },
                    'unit_amount': int(payment.amount * 100),  # Stripe usa centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(payment.student.id),
            metadata=metadata,
            idempotency_key=idem_key,
        )
        
        # Opcional: Audit Logging de início de sessão.
        log_audit_event(
            actor=request.user,
            action="stripe_checkout_initiated",
            target=payment,
            description="Redirecionando para portal seguro da Stripe",
            metadata={"session_id": session.id, "idempotency_key": idem_key}
        )

        return session.url
    except stripe.StripeError as e:
        log_audit_event(
            actor=request.user,
            action="stripe_checkout_failed",
            target=payment,
            description=f"Falha na malha da Stripe: {str(e)}",
        )
        raise RuntimeError(f"Erro de comunicação com a adquirente: {str(e)}")

__all__ = ['create_checkout_session', 'generate_idempotency_key']
