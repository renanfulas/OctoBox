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
    PublicWorkoutColdSignupView,
    PublicWorkoutGoogleCallbackView,
    PublicWorkoutGoogleStartView,
    PublicWorkoutLandingView,
    PublicWorkoutLoginView,
    PublicWorkoutSubscribeView,
)

urlpatterns = [
    path('', PublicWorkoutLandingView.as_view(), name='public-workout-landing'),
    path('login', PublicWorkoutLoginView.as_view(), name='public-workout-login'),
    path('login/google', PublicWorkoutGoogleStartView.as_view(), name='public-workout-oauth-google-start'),
    path('login/google/callback', PublicWorkoutGoogleCallbackView.as_view(), name='public-workout-oauth-google-callback'),
    path('subscribe', PublicWorkoutSubscribeView.as_view(), name='public-workout-subscribe'),
    path('cadastro', PublicWorkoutColdSignupView.as_view(), name='public-workout-cold-signup'),
    path('billing-portal', PublicWorkoutBillingPortalView.as_view(), name='public-workout-billing-portal'),
    path('stripe/webhook/', public_workout_stripe_webhook_receiver, name='public-workout-stripe-webhook'),
]
