from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from access.context_processors import role_navigation
from access.roles import ROLE_MANAGER


@override_settings(OPERATIONS_MANAGER_WORKSPACE_ENABLED=False)
class ManagerWorkspaceToggleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='manager_toggle_user',
            password='P@ssw0rd!234',
            email='manager-toggle@example.com',
        )
        manager_group, _ = Group.objects.get_or_create(name=ROLE_MANAGER)
        self.user.groups.add(manager_group)
        self.client.force_login(self.user)
        self.factory = RequestFactory()

    def test_role_operations_redirects_manager_to_dashboard_when_workspace_disabled(self):
        response = self.client.get(reverse('role-operations'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    def test_manager_workspace_returns_not_found_when_disabled(self):
        response = self.client.get(reverse('manager-workspace'))

        self.assertEqual(response.status_code, 404)

    def test_manager_sidebar_hides_operation_link_when_workspace_disabled(self):
        request = self.factory.get(reverse('dashboard'))
        request.user = self.user
        request.resolver_match = type('ResolverMatch', (), {'view_name': 'dashboard'})()

        context = role_navigation(request)
        hrefs = [item['href'] for item in context['sidebar_navigation']]

        self.assertNotIn(reverse('role-operations'), hrefs)
