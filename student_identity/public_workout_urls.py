"""
ARQUIVO: rotas do corredor de treinos que nao pertencem ao namespace de
um personal especifico (/renan/<slug>) — login, assinatura e webhook de
pagamento (S3 do CORDA).

POR QUE ELE EXISTE:
- D.000 do CORDA: uma unica entrada '/treinos/' em PUBLIC_SCHEMA_PATHS
  cobre as tres. Login (B1); subscribe e o webhook proprio chegam na
  Onda B2 (Fatia B).
"""

from django.urls import path

from public_workouts.stripe_handlers import public_workout_stripe_webhook_receiver

from .public_workout_views import (
    PublicWorkoutBillingPortalView,
    PublicWorkoutLoginView,
    PublicWorkoutSubscribeView,
)

urlpatterns = [
    path('login', PublicWorkoutLoginView.as_view(), name='public-workout-login'),
    path('subscribe', PublicWorkoutSubscribeView.as_view(), name='public-workout-subscribe'),
    path('billing-portal', PublicWorkoutBillingPortalView.as_view(), name='public-workout-billing-portal'),
    path('stripe/webhook/', public_workout_stripe_webhook_receiver, name='public-workout-stripe-webhook'),
]
