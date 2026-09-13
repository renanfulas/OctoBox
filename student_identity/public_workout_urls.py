"""
ARQUIVO: rotas do corredor de treinos que nao pertencem ao namespace de
um personal especifico (/renan/<slug>) — login e, mais adiante, webhook
de pagamento (S3 do CORDA).

POR QUE ELE EXISTE:
- D.000 do CORDA: uma unica entrada '/treinos/' em PUBLIC_SCHEMA_PATHS
  cobre as duas. So a rota de login existe nesta onda (B1) — o webhook
  chega na Onda B2.
"""

from django.urls import path

from .public_workout_views import PublicWorkoutLoginView

urlpatterns = [
    path('login', PublicWorkoutLoginView.as_view(), name='public-workout-login'),
]
