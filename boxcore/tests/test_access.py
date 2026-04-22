"""
ARQUIVO: testes do modulo de acesso.

POR QUE ELE EXISTE:
- Valida o fluxo de entrada, visao de papeis e bootstrap de grupos.

O QUE ESTE ARQUIVO FAZ:
1. Testa redirecionamento inicial.
2. Testa renderizacao da tela de acessos.
3. Testa criacao dos grupos padrao.
4. Testa presenca do papel DEV e permissoes importantes do sistema.

PONTOS CRITICOS:
- Se esses testes quebrarem, normalmente houve impacto em login, roles ou permissoes.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION


@override_settings(
    ALLOWED_HOSTS=['testserver', 'www.octoboxfit.com.br', 'app.octoboxfit.com.br', 'octoboxfit.com.br'],
    STUDENT_OAUTH_PUBLIC_BASE_URL='https://app.octoboxfit.com.br',
)
class AccessViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='owner',
            email='owner@example.com',
            password='senha-forte-123',
        )

    def test_home_renders_marketing_landing_for_anonymous_user(self):
        response = self.client.get(reverse('home'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu box com presença premium. Sua operação no controle.')
        self.assertContains(response, 'https://app.octoboxfit.com.br/login/')

    def test_login_route_renders_entry_hub(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Como voce quer entrar?')
        self.assertContains(response, 'Continuar com Google')
        self.assertContains(response, reverse('login-staff'))

    def test_staff_login_route_renders_internal_form(self):
        response = self.client.get(reverse('login-staff'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back, Leader.')
        self.assertContains(response, 'LOGIN TO YOUR BOX')
        self.assertContains(response, 'name="username"', html=False)

    def test_access_overview_renders_role_matrix(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('access-overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Criar perfil sem abrir o admin')
        self.assertContains(response, 'DEV')
        self.assertContains(response, 'Recepcao')
        self.assertNotContains(response, 'Editar e ativar perfis sem admin')

    def test_access_overview_shows_management_panel_only_when_requested(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('access-overview')}?manage_profiles=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar e ativar perfis sem admin')
        self.assertContains(response, 'Ocultar')

    def test_authenticated_shell_renders_logout_as_post_form(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('access-overview'))

        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'action="{}"'.format(reverse('logout')))
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(
            response,
            '<button type="submit" class="profile-menu-item is-danger" role="menuitem">Sair</button>',
            html=True,
        )

    def test_owner_can_create_access_profile_without_admin(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('access-overview'),
            {
                'full_name': 'Maria Operacao',
                'username': 'maria.operacao',
                'email': 'maria.operacao@example.com',
                'password': 'SenhaTemporaria@123',
                'role': ROLE_MANAGER,
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = get_user_model().objects.get(username='maria.operacao')
        self.assertEqual(created_user.first_name, 'Maria')
        self.assertEqual(created_user.last_name, 'Operacao')
        self.assertTrue(created_user.groups.filter(name=ROLE_MANAGER).exists())

    def test_owner_can_update_access_profile_without_admin(self):
        target_user = get_user_model().objects.create_user(
            username='joao.time',
            email='joao@old.example.com',
            password='Senha@123',
            first_name='Joao',
            last_name='Time',
        )
        target_user.groups.add(Group.objects.create(name=ROLE_RECEPTION))
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('access-overview'),
            {
                'access_action': 'update',
                'target_profile_id': str(target_user.id),
                f'profile-{target_user.id}-full_name': 'Joao Gestor',
                f'profile-{target_user.id}-email': 'joao@new.example.com',
                f'profile-{target_user.id}-role': ROLE_MANAGER,
            },
        )

        self.assertEqual(response.status_code, 302)
        target_user.refresh_from_db()
        self.assertEqual(target_user.first_name, 'Joao')
        self.assertEqual(target_user.last_name, 'Gestor')
        self.assertEqual(target_user.email, 'joao@new.example.com')
        self.assertTrue(target_user.groups.filter(name=ROLE_MANAGER).exists())

    def test_owner_can_toggle_access_profile_status_without_admin(self):
        target_user = get_user_model().objects.create_user(
            username='ana.time',
            email='ana@example.com',
            password='Senha@123',
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('access-overview'),
            {
                'access_action': 'toggle_active',
                'target_profile_id': str(target_user.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        target_user.refresh_from_db()
        self.assertFalse(target_user.is_active)


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

    def test_owner_group_receives_student_invitation_admin_permissions(self):
        call_command('bootstrap_roles')

        owner_group = Group.objects.get(name=ROLE_OWNER)

        self.assertTrue(owner_group.permissions.filter(codename='view_studentappinvitation').exists())
        self.assertTrue(owner_group.permissions.filter(codename='change_studentappinvitation').exists())

    def test_dev_group_receives_student_invitation_visibility(self):
        call_command('bootstrap_roles')

        dev_group = Group.objects.get(name=ROLE_DEV)

        self.assertTrue(dev_group.permissions.filter(codename='view_studentappinvitation').exists())
