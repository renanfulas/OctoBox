"""
ARQUIVO: rotas do guia interno do sistema.

POR QUE ELE EXISTE:
- Separa as páginas pedagógicas e de apoio técnico do restante da aplicação.

O QUE ESTE ARQUIVO FAZ:
1. Publica a página Mapa do Sistema.

PONTOS CRITICOS:
- Mudança no nome da rota impacta links do menu e testes.
"""

from django.urls import path

from .views import SystemMapView

urlpatterns = [
    path('mapa-sistema/', SystemMapView.as_view(), name='system-map'),
]