"""
ARQUIVO: testes da página de guia interno.

POR QUE ELE EXISTE:
- Garante que a página Mapa do Sistema continue acessível e útil para leitura do projeto.

O QUE ESTE ARQUIVO FAZ:
1. Testa renderização da página autenticada.
2. Valida a presença de conteúdos centrais do mapa.

PONTOS CRITICOS:
- Se esses testes falharem, a página de orientação interna pode ter quebrado ou perdido contexto.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class GuideViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='owner-guide',
            email='owner-guide@example.com',
            password='senha-forte-123',
        )

    def test_system_map_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('system-map'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mapa do Sistema')
        self.assertContains(response, 'Primeira triagem por sintoma')
        self.assertContains(response, 'Rotina operacional do box')
        self.assertContains(response, 'Sidebar ou atalhos errados para o papel')
        self.assertContains(response, 'Auditoria')
        self.assertContains(response, 'DEV')
        self.assertContains(response, 'href="#system-flow-board"')
        self.assertContains(response, 'href="#system-reading-board"')
        self.assertContains(response, 'href="#system-bug-board"')

    def test_operational_settings_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('operational-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configuracoes operacionais')
        self.assertContains(response, 'OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS')
        self.assertContains(response, 'Financeiro: regua de cobranca e retencao.')