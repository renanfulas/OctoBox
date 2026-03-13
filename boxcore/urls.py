"""
ARQUIVO: agregador legado de rotas do boxcore.

POR QUE ELE EXISTE:
- Preserva compatibilidade para imports historicos de boxcore.urls.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as mesmas rotas canonicas do runtime.
2. Evita quebra enquanto referencias antigas ainda existirem.

PONTOS CRITICOS:
- O roteador raiz oficial agora e config.urls.
- Este modulo nao deve voltar a concentrar novas decisoes de roteamento.
"""

from django.urls import include, path

urlpatterns = [
    path('', include('access.urls')),
    path('api/', include('api.urls')),
    path('', include('boxcore.dashboard.urls')),
    path('', include('catalog.urls')),
    path('', include('boxcore.guide.urls')),
    path('', include('operations.urls')),
]