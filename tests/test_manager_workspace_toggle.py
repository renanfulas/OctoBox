from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from access.roles import ROLE_MANAGER, ROLE_RECEPTION


class ManagerWorkspaceToggleTests(TestCase):
    def setUp(self):
        call_command('bootstrap_roles')
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username='manager-toggle',
            email='manager-toggle@example.com',
            password='senha-forte-123',
        )
        self.reception = user_model.objects.create_user(
            username='reception-toggle',
            email='reception-toggle@example.com',
            password='senha-forte-123',
        )
        self.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

    def test_manager_workspace_route_remains_available_for_manager_role(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 200)

    def test_manager_workspace_route_stays_blocked_for_reception_role(self):
        self.client.force_login(self.reception)

        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 403)
