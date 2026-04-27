"""
ARQUIVO: Gateway de saída para Checkout Stripe.

POR QUE ELE EXISTE:
- Protege a chamada do backend da Stripe contra bots (card-testing).
- Transfere o fluxo UX do OctoBox para os servidores PCI-compliant da Stripe.

O QUE ESTE ARQUIVO FAZ:
1. Aplica um rate limit simples por IP+usuário (cache).
2. Valida o Payment antes de abrir o checkout.
3. Chama `create_checkout_session` e redireciona para a Stripe.
4. Renderiza páginas de retorno (sucesso/cancelamento) com fachada estável.
"""

from __future__ import annotations

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from finance.models import Payment
from integrations.stripe.services import create_checkout_session

logger = logging.getLogger(__name__)


class StripeCheckoutRedirectView(LoginRequiredMixin, View):
    """
    Inicia um checkout seguro.

    Observação:
    - Esta view é navegação (redirect), então fica fora do DRF e seus throttles.
    - O rate limit aqui é um guardrail pragmático para reduzir card-testing.
    """

    def post(self, request, payment_id: int):
        ip = request.META.get("REMOTE_ADDR")
        key = f"octo_stripe_rl_{ip}_{request.user.id}"
        attempts = cache.get(key, 0)

        if attempts >= 10:
            logger.warning("Suspeita de EXAUSTÃO/CARD-TESTING. Bloqueando %s.", ip)
            return render(request, "429.html", status=429)

        cache.set(key, attempts + 1, timeout=3600)

        payment = get_object_or_404(Payment, pk=payment_id)

        if payment.status == "paid":
            return render(request, "400.html", {"error": "Fatura já liquidada."}, status=400)

        try:
            url = create_checkout_session(payment, request)
            return redirect(url)
        except Exception as exc:
            logger.error("Erro ao instanciar Stripe Session: %s", exc, exc_info=True)
            return render(
                request,
                "500.html",
                {"error": "Gateway de Pagamento temporariamente indisponível."},
                status=500,
            )


class StripeCheckoutSuccessView(View):
    """
    Callback de retorno visual da Stripe.

    Importante:
    - Não dá baixa de banco; isso é responsabilidade do webhook.
    """

    def get(self, request, *args, **kwargs):
        return render(request, "finance/checkout_success.html")


class StripeCheckoutCancelView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "finance/checkout_cancel.html")


__all__ = [
    "StripeCheckoutRedirectView",
    "StripeCheckoutSuccessView",
    "StripeCheckoutCancelView",
]
