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

from guide.models import OperationalRuntimeSetting


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
        self.assertContains(response, 'data-panel="system-flow-grid"')
        self.assertContains(response, 'id="system-reading-board"')
        self.assertContains(response, 'id="system-bug-board"')

    def test_operational_settings_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('operational-settings'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operacao configurada.')
        self.assertContains(response, 'Salvar bloqueio do WhatsApp')
        self.assertContains(response, 'Criar perfis de acesso')

    def test_operational_settings_can_update_whatsapp_repeat_window(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('operational-settings'), {'repeat_block_hours': '12'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            OperationalRuntimeSetting.objects.get(key='whatsapp_repeat_block_hours').value,
            '12',
        )
