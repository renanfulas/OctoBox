"""
ARQUIVO: rotas da Central de Intake.

POR QUE ELE EXISTE:
- Publica a superficie HTTP propria do modulo de onboarding.
"""

from django.urls import path

from .views import IntakeCenterView, IntakeSearchIndexPageView


urlpatterns = [
    path('entradas/', IntakeCenterView.as_view(), name='intake-center'),
    path('entradas/indice/', IntakeSearchIndexPageView.as_view(), name='intake-search-index-page'),
]
