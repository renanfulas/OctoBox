"""
ARQUIVO: rotas do dashboard.

POR QUE ELE EXISTE:
- mantem as rotas canonicas do painel em um bloco proprio fora do legado.

O QUE ESTE ARQUIVO FAZ:
1. publica a tela principal do dashboard.

PONTOS CRITICOS:
- mudanca no nome da rota impacta login, redirecionamentos e testes.
"""

from django.urls import path

from .dashboard_views import DashboardView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]