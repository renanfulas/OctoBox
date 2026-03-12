"""
ARQUIVO: views iniciais da API v1.

POR QUE ELE EXISTE:
- Fornece endpoints minimos de saude e manifesto para preparar clientes externos e app mobile.

O QUE ESTE ARQUIVO FAZ:
1. Publica o manifesto da versao v1.
2. Publica um endpoint de saude estavel.

PONTOS CRITICOS:
- Endpoints versionados devem permanecer previsiveis e pequenos.
"""

from django.http import JsonResponse
from django.views import View


class ApiV1ManifestView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'version': 'v1',
                'status': 'active',
                'resources': {
                    'health': '/api/v1/health/',
                },
                'scope': [
                    'foundation',
                    'mobile-ready-boundary',
                    'integration-ready-boundary',
                ],
            }
        )


class ApiV1HealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'status': 'ok',
                'version': 'v1',
                'product': 'OctoBox Control',
                'api_boundary': 'stable-entrypoint',
            }
        )
