"""
ARQUIVO: testes da fronteira inicial de API.

POR QUE ELE EXISTE:
- Garante que a entrada versionada da API continue estavel enquanto o produto cresce.

O QUE ESTE ARQUIVO FAZ:
1. Testa o indice da API.
2. Testa o manifesto da v1.
3. Testa a rota de saude da v1.

PONTOS CRITICOS:
- Essas rotas viram contrato para mobile e integracoes futuras.
"""

import os
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class ApiFoundationTests(TestCase):
    def test_api_root_exposes_available_versions(self):
        response = self.client.get(reverse('api-root'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['kind'], 'api-root')
        self.assertIn('v1', response.json()['available_versions'])

    def test_api_v1_manifest_exposes_health_resource(self):
        response = self.client.get(reverse('api-v1-manifest'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], 'v1')
        self.assertEqual(response.json()['resources']['health'], '/api/v1/health/')

    def test_api_v1_health_reports_ok(self):
        response = self.client.get(reverse('api-v1-health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['api_boundary'], 'stable-entrypoint')

    def test_api_v1_health_exposes_runtime_boundary(self):
        with patch.dict(os.environ, {'BOX_RUNTIME_SLUG': 'box-piloto-centro'}, clear=False):
            response = self.client.get(reverse('api-v1-health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['runtime_slug'], 'box-piloto-centro')
        self.assertEqual(response.json()['runtime_namespace'], 'octobox:box-piloto-centro')
