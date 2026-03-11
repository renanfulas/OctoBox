"""
ARQUIVO: rotas do dashboard.

POR QUE ELE EXISTE:
- Mantém as rotas do painel em um bloco visual próprio.

O QUE ESTE ARQUIVO FAZ:
1. Publica a tela principal do dashboard.

PONTOS CRITICOS:
- Mudança no nome da rota impacta login, redirecionamentos e testes.
"""

from django.urls import path

from .dashboard_views import DashboardView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]