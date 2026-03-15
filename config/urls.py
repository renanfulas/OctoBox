"""
ARQUIVO: roteador principal de URLs do projeto.

POR QUE ELE EXISTE:
- Junta em um só lugar as rotas reais do sistema e o admin.

O QUE ESTE ARQUIVO FAZ:
1. Publica as rotas HTTP canonicas do runtime atual.
2. Mantém o admin do Django ativo em /admin/.

PONTOS CRITICOS:
- A ordem dos includes afeta a resolucao de URLs concorrentes.
- Mudanças erradas aqui podem gerar 404 em massa.
"""
from django.contrib import admin
from django.conf import settings
from django.urls import include, path

from access.admin import install_admin_site_gate


install_admin_site_gate()

urlpatterns = [
    path('', include('access.urls')),
    path('api/', include('api.urls')),
    path('', include('dashboard.urls')),
    path('', include('catalog.urls')),
    path('', include('guide.urls')),
    path('', include('operations.urls')),
    path(settings.ADMIN_URL_PATH, admin.site.urls),
]
