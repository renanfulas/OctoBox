from django.test import TestCase, RequestFactory

from access import context_processors
from access import shell_actions
from access.roles import ROLE_RECEPTION
from django.contrib.auth import get_user_model


class ShellActionsAndContextTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='pwd')

    def test_resolve_shell_scope_various(self):
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/dashboard/'), 'dashboard')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/dashboard/', role_slug=ROLE_RECEPTION), 'dashboard-reception')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/entradas/'), 'intake-center')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/alunos/novo/'), 'student-form')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/financeiro/planos/'), 'finance-plan-form')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/grade-aulas/'), 'class-grid')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/acessos/'), 'access')
        self.assertEqual(shell_actions.resolve_shell_scope(current_path='/unknown/'), 'generic')

    def test_build_shell_action_buttons_counts(self):
        counts = {'overdue_payments': 2, 'pending_intakes': 3, 'sessions_today': 0}
        buttons = shell_actions.build_shell_action_buttons(counts=counts)
        self.assertEqual(len(buttons), 3)
        # priority should carry overdue_payments count
        self.assertEqual(buttons[0]['kind'], 'priority')
        self.assertEqual(buttons[0]['count'], 2)
        # pending should carry pending_intakes
        self.assertEqual(buttons[1]['kind'], 'pending')
        self.assertEqual(buttons[1]['count'], 3)
        # next-action had 0 sessions_today so should be None
        self.assertIsNone(buttons[2]['count'])

    def test_build_shell_action_buttons_from_focus_and_attach(self):
        focus = [
            {'label': 'One', 'href': '/one/', 'chip_label': 'X'},
            {'label': 'Two', 'href': '/two/', 'chip_label': 'Y'},
        ]
        ctx = {}
        new_ctx = shell_actions.attach_shell_action_buttons(ctx, focus=focus, counts={'overdue_payments': 1, 'pending_intakes': 0, 'sessions_today': 5})
        self.assertIn('shell_action_buttons', new_ctx)
        buttons = new_ctx['shell_action_buttons']
        self.assertEqual(buttons[0]['label'], 'X')
        self.assertEqual(buttons[1]['label'], 'Y')

    def test_build_default_shell_action_buttons_dashboard_and_entradas(self):
        # dashboard standard
        btns = shell_actions.build_default_shell_action_buttons(current_path='/dashboard/', role_slug='Owner', overdue_payments=1, pending_intakes=2, sessions_today=3)
        self.assertTrue(any(b['kind'] == 'priority' for b in btns))

        # entradas path
        btns2 = shell_actions.build_default_shell_action_buttons(current_path='/entradas/', role_slug='Owner')
        self.assertEqual(btns2[0]['label'], 'Fila')

    def test_role_navigation_anonymous_and_authenticated(self):
        # anonymous
        req = self.rf.get('/')
        req.user = get_user_model().objects.create_user(username='anon')
        # mark as unauthenticated
        req.user.is_authenticated = False
        ctx = context_processors.role_navigation(req)
        self.assertIn('sidebar_navigation', ctx)

        # authenticated
        req2 = self.rf.get('/acessos/')
        req2.user = self.user
        ctx2 = context_processors.role_navigation(req2)
        self.assertTrue(len(ctx2.get('sidebar_navigation', [])) > 0)
        # ensure acessos link exists
        hrefs = [i.get('href') for i in ctx2.get('sidebar_navigation', [])]
        self.assertIn('/acessos/', hrefs)
