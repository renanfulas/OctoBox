"""
ARQUIVO: agregador de rotas internas do boxcore.

POR QUE ELE EXISTE:
- Centraliza os módulos de rota por assunto sem misturar lógica de tela.

O QUE ESTE ARQUIVO FAZ:
1. Liga o módulo de acesso.
2. Liga o módulo de dashboard.
3. Liga páginas visuais de catálogo.

PONTOS CRITICOS:
- Se um include sair daqui, a área correspondente deixa de responder.
"""

from django.urls import include, path

urlpatterns = [
    path('', include('access.urls')),
    path('api/', include('api.urls')),
    path('', include('boxcore.dashboard.urls')),
    path('', include('boxcore.catalog.urls')),
    path('', include('boxcore.guide.urls')),
    path('', include('boxcore.operations.urls')),
]