"""
ARQUIVO: rotas publicas do fluxo Early Adopter.

POR QUE ELE EXISTE:
- Mantem o checkout publico fora do escopo do app `access` (que cuida de login).
- Concentra os 3 estados do fluxo: form, sucesso, cancelado.

O QUE ESTE ARQUIVO FAZ:
1. /checkout/                  -> form do plano escolhido (?plan=annual|monthly).
2. /checkout/sucesso/          -> pos-pagamento (callback success do Stripe).
3. /checkout/cancelado/        -> callback cancel do Stripe.
4. /checkout/aguardando/<id>/  -> fallback dev/manual (quando Stripe nao configurado).
"""
from django.urls import path

from .views import (
    CheckoutCanceledView,
    CheckoutFormView,
    CheckoutPendingStripeView,
    CheckoutSuccessView,
    OnboardingWizardView,
    ThankYouView,
)

urlpatterns = [
    path('checkout/', CheckoutFormView.as_view(), name='signup-checkout'),
    path('checkout/sucesso/', CheckoutSuccessView.as_view(), name='signup-checkout-success'),
    path('checkout/cancelado/', CheckoutCanceledView.as_view(), name='signup-checkout-canceled'),
    path('checkout/aguardando/<int:pending_id>/', CheckoutPendingStripeView.as_view(), name='signup-checkout-pending'),
    path('onboarding/<str:token>/', OnboardingWizardView.as_view(), name='signup-onboarding'),
    path('obrigado/', ThankYouView.as_view(), name='signup-thank-you'),
]
