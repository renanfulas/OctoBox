"""
ARQUIVO: roteador principal de URLs do projeto.

POR QUE ELE EXISTE:
- Junta em um só lugar as rotas do app e do admin.

O QUE ESTE ARQUIVO FAZ:
1. Encaminha as rotas do boxcore.
2. Mantém o admin do Django ativo em /admin/.

PONTOS CRITICOS:
- Se um include for removido ou quebrado, áreas inteiras do sistema somem.
- Mudanças erradas aqui podem gerar 404 em massa.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('boxcore.urls')),
    path('admin/', admin.site.urls),
]
