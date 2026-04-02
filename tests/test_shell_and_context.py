"""
ARQUIVO: testes enxutos do shell autenticado.

POR QUE ELE EXISTE:
- protege o que ainda esta vivo no shell depois da remocao do page compass.
"""

from django.conf import settings
from django.test import TestCase

from access import shell_actions
from access.roles import ROLE_RECEPTION


class ShellActionsAndContextTests(TestCase):
    def test_resolve_shell_scope_various(self):
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='dashboard'), 'dashboard')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='dashboard', role_slug=ROLE_RECEPTION), 'dashboard-reception')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='intake-center'), 'intake')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='student-quick-create'), 'student-form')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='membership-plan-quick-update'), 'finance-plan-form')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='class-grid'), 'class-grid')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='owner-workspace'), 'operations-owner')
        self.assertEqual(shell_actions.resolve_shell_scope(view_name='unknown-view'), 'generic')
        self.assertEqual(
            shell_actions.resolve_shell_scope(fallback_path=f'/{settings.ADMIN_URL_PATH}'),
            'admin',
        )

    def test_get_shell_counts_contract_has_expected_keys(self):
        counts = shell_actions.get_shell_counts(use_cache=False)

        self.assertIn('overdue_payments', counts)
        self.assertIn('pending_intakes', counts)
        self.assertIn('sessions_today', counts)
        self.assertIn('active_students', counts)
