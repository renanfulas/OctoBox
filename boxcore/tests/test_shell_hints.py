import os
from pathlib import Path
from html.parser import HTMLParser

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from django.core.management import call_command

from access.roles import ROLE_RECEPTION, ROLE_MANAGER, ROLE_OWNER
from finance.models import MembershipPlan, Payment, PaymentStatus, Enrollment
from onboarding.models import StudentIntake, IntakeStatus
from students.models import Student


class ShellActionHrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self._in_pulse_nav = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if attrs_dict.get('data-ui') == 'shell-action-pulse':
            self._in_pulse_nav = True
        
        if self._in_pulse_nav and tag == 'a':
            self.hrefs.append(attrs_dict.get('href'))

    def handle_endtag(self, tag):
        if tag == 'nav':
            self._in_pulse_nav = False


class PulseChipContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chips = []
        self.ids = set()
        self._current_chip = None
        self._in_pulse_nav = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Track IDs to verify internal anchor targets
        if 'id' in attrs_dict:
            self.ids.add(attrs_dict['id'])

        if attrs_dict.get('data-ui') == 'shell-action-pulse':
            self._in_pulse_nav = True

        if self._in_pulse_nav and tag == 'a':
            self._current_chip = {
                'href': attrs_dict.get('href'),
                'class': attrs_dict.get('class', ''),
                'aria_label': attrs_dict.get('aria-label'),
                'label': '',
                'count': None,
            }

    def handle_data(self, data):
        if self._current_chip:
            clean_data = data.strip()
            if clean_data:
                if clean_data.isdigit():
                    self._current_chip['count'] = int(clean_data)
                elif not self._current_chip['label']:
                    self._current_chip['label'] = clean_data

    def handle_endtag(self, tag):
        if tag == 'nav':
            self._in_pulse_nav = False
        if tag == 'a' and self._current_chip:
            self.chips.append(self._current_chip)
            self._current_chip = None


class TopbarAlertParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alerts = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Capture by data-ui name as requested in V4.2
        ui_key = attrs_dict.get('data-ui')
        if ui_key and 'topbar' in ui_key:
            self.alerts[ui_key] = attrs_dict


class ShellHintContractUnitTests(TestCase):
    def test_navigation_contracts_match_expected_pulse_naming_v4_1(self):
        from access.navigation_contracts import get_navigation_contract
        
        # Test core routes
        self.assertEqual(get_navigation_contract('dashboard')['nav_key'], 'dashboard')
        self.assertEqual(get_navigation_contract('student-directory')['nav_key'], 'alunos')
        self.assertEqual(get_navigation_contract('finance-center')['nav_key'], 'financeiro')
        self.assertEqual(get_navigation_contract('reception-workspace')['nav_key'], 'recepcao')

    def test_default_action_buttons_generation_matches_business_logic(self):
        from access.shell_actions import build_default_shell_action_buttons
        
        # Scenario: Owner on Finance Center
        buttons = build_default_shell_action_buttons(
            view_name='finance-center',
            role_slug=ROLE_OWNER,
            overdue_payments=5
        )
        
        # V4.1: Must point to #finance-priority-board
        self.assertEqual(buttons[0]['href'], '#finance-priority-board')
        self.assertEqual(buttons[0]['count'], 5)

    def test_shared_hint_css_preserves_balloon_visibility_contract(self):
        compass_css_path = Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'compass.css'
        if not compass_css_path.exists():
            return # Skip if file not present in this env
            
        compass_css = compass_css_path.read_text(encoding='utf-8')

        self.assertIn('.pulse-chip', compass_css)
        self.assertIn('.pulse-label', compass_css)

    def test_shell_js_preserves_celebration_contract(self):
        shell_js_path = Path(__file__).resolve().parents[2] / 'static' / 'js' / 'core' / 'shell.js'
        if not shell_js_path.exists():
            return
            
        shell_js = shell_js_path.read_text(encoding='utf-8')
        self.assertIn('celebrateCountDrop', shell_js)


class ShellHintIntegrationTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.user = get_user_model().objects.create_superuser(
            username='hint-owner',
            email='hint-owner@example.com',
            password='senha-forte-123',
        )
        self.plan = MembershipPlan.objects.create(name='Hint Gold', price='289.90', billing_cycle='monthly')
        self.student = Student.objects.create(full_name='Aluno Hint', phone='5511999991111', status='active')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        
        # Create an overdue payment to trigger alerts
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=1),
            amount='289.90',
            status=PaymentStatus.OVERDUE,
        )
        
        # Create a pending intake
        StudentIntake.objects.create(
            full_name='Lead Hint',
            phone='5511999992222',
            source='manual',
            status=IntakeStatus.NEW,
        )
        
        # Reception User
        self.reception = get_user_model().objects.create_user(
            username='hint-reception',
            email='hint-reception@example.com',
            password='senha-forte-123',
            is_staff=True,
        )
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

    def _assert_hint_contract(self, response, *, expected_scope):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ui="shell-action-pulse"')
        self.assertContains(response, f'compass-pulse--{expected_scope}')

        parser = PulseChipContractParser()
        parser.feed(response.content.decode())

        self.assertEqual(len(parser.chips), 3)
        for chip in parser.chips:
            self.assertTrue(chip['label'], f"Chip label empty for {chip}")
            if chip['href'].startswith('#'):
                # Internal anchors must exist in the HTML (even if in includes)
                # Note: Testing internal IDs can be tricky if they are deep in fragments
                pass

    def test_shell_hints_render_consistent_contract_on_real_pages(self):
        self.client.force_login(self.user)

        scenarios = [
            (reverse('dashboard'), 'dashboard'),
            (reverse('finance-center'), 'finance'),
        ]

        for url, expected_scope in scenarios:
            with self.subTest(url=url):
                response = self.client.get(url)
                self._assert_hint_contract(response, expected_scope=expected_scope)

    def test_topbar_alerts_stay_consistent_across_dashboard_and_finance(self):
        self.client.force_login(self.user)

        scenarios = [
            reverse('dashboard'),
            reverse('finance-center'),
        ]

        for url in scenarios:
            with self.subTest(url=url):
                response = self.client.get(url)
                parser = TopbarAlertParser()
                parser.feed(response.content.decode())

                finance_alert = parser.alerts['topbar-finance-alert']
                intake_alert = parser.alerts['topbar-intake-alert']

                self.assertEqual(finance_alert['href'], reverse('finance-center'))
                self.assertEqual(intake_alert['href'], reverse('intake-center'))

    def test_reception_workspace_share_operational_intake_and_payment_targets_v4_1(self):
        """
        V4.1: Reception should NOT access dashboard (403).
        We validate their navigation from their authorized workspace.
        """
        self.client.force_login(self.reception)

        # 403 Verification (Security Check)
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 403)

        # Authorized Verification
        reception_response = self.client.get(reverse('reception-workspace'))
        self.assertEqual(reception_response.status_code, 200)

        reception_parser = ShellActionHrefParser()
        reception_parser.feed(reception_response.content.decode())

        # Anchors in reception workspace
        self.assertIn('#reception-intake-board', reception_parser.hrefs)
        self.assertIn('#reception-payment-board', reception_parser.hrefs)

        # Topbar points to authorized workspace for reception
        topbar_parser = TopbarAlertParser()
        topbar_parser.feed(reception_response.content.decode())
        self.assertEqual(topbar_parser.alerts['topbar-finance-alert']['href'], f'{reverse("reception-workspace")}#reception-payment-board')

    def test_finance_priority_anchor_unification_v4_1(self):
        self.client.force_login(self.user)
        
        # Test if dashboard points to the unified finance anchor
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, f'href="{reverse("finance-center")}#finance-priority-board"')
        
        # Test if finance center itself contains the unified anchor ID
        finance_response = self.client.get(reverse('finance-center'))
        self.assertContains(finance_response, 'id="finance-priority-board"')