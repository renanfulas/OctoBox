"""
ARQUIVO: testes do módulo de acesso.

POR QUE ELE EXISTE:
- Valida o fluxo de entrada, visão de papéis e bootstrap de grupos.

O QUE ESTE ARQUIVO FAZ:
1. Testa redirecionamento inicial.
2. Testa renderização da tela de acessos.
3. Testa criação dos grupos padrão.
4. Testa presença do papel DEV e permissões importantes do sistema.

PONTOS CRITICOS:
- Se esses testes quebrarem, normalmente houve impacto em login, roles ou permissões.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION


class AccessViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='owner',
            email='owner@example.com',
            password='senha-forte-123',
        )

    def test_home_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('login'))

    def test_access_overview_renders_role_matrix(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('access-overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Papéis e acessos')
        self.assertContains(response, 'DEV')
        self.assertContains(response, 'Recepcao')

    def test_authenticated_shell_renders_logout_as_post_form(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('access-overview'))

        self.assertContains(response, 'class="sidebar-logout-form"')
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'action="{}"'.format(reverse('logout')))
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, '<button class="nav-link nav-link-button" type="submit"><span class="nav-icon">🚪</span>Sair</button>', html=True)


class BootstrapRolesCommandTests(TestCase):
    def test_command_creates_default_groups(self):
        call_command('bootstrap_roles')

        self.assertTrue(Group.objects.filter(name=ROLE_OWNER).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_DEV).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_MANAGER).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_RECEPTION).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_COACH).exists())

    def test_manager_group_receives_payment_visibility(self):
        call_command('bootstrap_roles')

        manager_group = Group.objects.get(name=ROLE_MANAGER)

        self.assertTrue(manager_group.permissions.filter(codename='view_payment').exists())

    def test_dev_group_receives_audit_visibility(self):
        call_command('bootstrap_roles')

        dev_group = Group.objects.get(name=ROLE_DEV)

        self.assertTrue(dev_group.permissions.filter(codename='view_auditevent').exists())