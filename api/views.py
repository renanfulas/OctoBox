"""
ARQUIVO: views base da fronteira de API do produto.

POR QUE ELE EXISTE:
- Expoe a entrada institucional da API sem depender da interface web interna.

O QUE ESTE ARQUIVO FAZ:
1. Publica o indice da API.
2. Lista versoes disponiveis.
3. Deixa explicito que clientes externos devem entrar por esta fronteira.

PONTOS CRITICOS:
- A resposta aqui funciona como contrato de descoberta para clientes futuros.
"""

from django.http import JsonResponse
from django.views import View


class ApiRootView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'product': 'OctoBox Control',
                'kind': 'api-root',
                'status': 'ready-for-growth',
                'available_versions': ['v1'],
                'notes': 'A API versionada sera expandida em paralelo a interface web interna.',
            }
        )
