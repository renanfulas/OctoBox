"""
ARQUIVO: testes do dashboard.

POR QUE ELE EXISTE:
- Garante que o painel principal continue acessível e renderizando o básico.

O QUE ESTE ARQUIVO FAZ:
1. Testa proteção por login.
2. Testa renderização do painel autenticado.

PONTOS CRITICOS:
- Se esses testes falharem, pode ter quebrado rota, template ou contexto do dashboard.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from boxcore.models import MembershipPlan, Student


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='gestor',
            email='gestor@example.com',
            password='senha-forte-123',
        )
        MembershipPlan.objects.create(name='Mensal 3x', price='249.90')
        Student.objects.create(full_name='Ana Silva', phone='5511999999999')

    def test_redirects_when_user_is_not_authenticated(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operação do box em um painel só.')
        self.assertContains(response, 'Owner')