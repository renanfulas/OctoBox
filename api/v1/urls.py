"""
ARQUIVO: rotas da API v1.

POR QUE ELE EXISTE:
- Organiza os endpoints da primeira versao da API em um bloco proprio.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da v1.
2. Publica a rota de saude da v1.

PONTOS CRITICOS:
- Nomes e caminhos daqui viram contrato publico da API.
"""

from django.urls import path

from .views import ApiV1HealthView, ApiV1ManifestView, StudentAutocompleteView


urlpatterns = [
    path('', ApiV1ManifestView.as_view(), name='api-v1-manifest'),
    path('health/', ApiV1HealthView.as_view(), name='api-v1-health'),
    path('students/autocomplete/', StudentAutocompleteView.as_view(), name='api-v1-student-autocomplete'),
]
