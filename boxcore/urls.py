"""
ARQUIVO: agregador legado de rotas do boxcore.

POR QUE ELE EXISTE:
- preserva compatibilidade para imports historicos de boxcore.urls.

O QUE ESTE ARQUIVO FAZ:
1. espelha as mesmas rotas canonicas do runtime atual.
2. evita quebra enquanto referencias antigas ainda existirem.

PONTOS CRITICOS:
- o roteador raiz oficial agora e config.urls.
- este modulo nao deve voltar a concentrar novas decisoes de roteamento.
"""

from django.urls import include, path

urlpatterns = [
    path('', include('access.urls')),
    path('api/', include('api.urls')),
    path('', include('dashboard.urls')),
    path('', include('catalog.urls')),
    path('', include('guide.urls')),
    path('', include('operations.urls')),
]

__all__ = ['urlpatterns']