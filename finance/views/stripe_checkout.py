"""
ARQUIVO: Gateway de saída para Checkout Stripe.

POR QUE ELE EXISTE:
- Protege a chamada do backend da Stripe contra Bots (Card-Testing).
- Transfere o Flow UX do OctoBox para os servidores PCI-Compliant da Stripe.

O QUE ESTE ARQUIVO FAZ:
1. Aplica o Rate Limiting `AntiCardTestingUserThrottle`.
2. Intercepta requisições inválidas antes do processamento JSON.
3. Chama a Service de `create_checkout_session` e redireciona.

"""

import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_400pass, redirect, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from finance.models import Payment
from integrations.stripe.services import create_checkout_session

logger = logging.getLogger(__name__)

class StripeCheckoutRedirectView(LoginRequiredMixin, View):
    """
    Inicia um checkout seguro.
    Não usamos REST framework nesta View para manter navegação pura,
    então os Throttles de DRF não se aplicam por decorator simples,
    podemos aplicar ratelimit na camada proxy ou middleware, ou criar 
    uma verificação manual do Cache baseada na lógica de Anon/User RateThrottle.
    Para fins de simulação OctoBox-Fintech, o cache será gerenciado diretamente.
    """
    
    def post(self, request, payment_id):
        # Proteção: Garantir que apenas usuários logados (Dono, Recepcão) 
        # ou o próprio dono do pagamento disparem esse gateway.
        # No Octobox atual, quem clica em "Pagar" é a recepção.
        
        # 🛡️ Blindagem: Ratelimit Simples em Memória Redis
        from django.core.cache import cache
        ip = request.META.get('REMOTE_ADDR')
        key = f"octo_stripe_rl_{ip}_{request.user.id}"
        attempts = cache.get(key, 0)
        
        if attempts >= 10:  # 10 checkouts abertos por hora por esse device
            logger.warning(f"Suspeita de EXAUSTÃO/CARD-TESTING. Bloqueando {ip}.")
            return render(request, "429.html", status=429)
            
        cache.set(key, attempts + 1, timeout=3600)

        # Tranca do banco: Ler o Payment garantindo que existe
        payment = get_object_or_400pass(Payment, pk=payment_id)
        
        if payment.status == 'paid':
             return render(request, "400.html", {"error": "Fatura já liquidada."})

        try:
            url = create_checkout_session(payment, request)
            return redirect(url)
        except Exception as e:
            logger.error(f"Erro ao instanciar Stripe Session: {str(e)}")
            return render(request, "500.html", {"error": "Gateway de Pagamento temporariamente indisponível."})


class StripeCheckoutSuccessView(View):
    """Callback de retorno visual da Stripe (Não dá baixa de banco, isso é o Webhook que faz)"""
    def get(self, *args, **kwargs):
        # Apenas renderiza a tela bonita avisando "Pagamento em Processamento"
        # O Webhook por baixo dos panos finaliza a transação.
        return render(self.request, "finance/checkout_success.html")


class StripeCheckoutCancelView(View):
    def get(self, *args, **kwargs):
        return render(self.request, "finance/checkout_cancel.html")


__all__ = ['StripeCheckoutRedirectView', 'StripeCheckoutSuccessView', 'StripeCheckoutCancelView']
