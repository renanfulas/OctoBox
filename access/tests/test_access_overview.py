from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_OWNER


class AccessOverviewViewTests(TestCase):
    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='access-owner',
            password='senha-forte-123',
            email='access-owner@example.com',
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.client.force_login(self.owner)

    def test_access_overview_renders_for_owner(self):
        response = self.client.get(reverse('access-overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Papeis e acessos')

    def test_access_overview_can_create_profile(self):
        response = self.client.post(
            reverse('access-overview'),
            data={
                'access_action': 'create',
                'full_name': 'Perfil Novo',
                'username': 'perfil.novo',
                'email': 'perfil.novo@example.com',
                'password': 'Senha-temporaria-123',
                'role': ROLE_OWNER,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='perfil.novo').exists())
