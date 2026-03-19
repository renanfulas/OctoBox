"""
ARQUIVO: testes da estrutura compartilhada de hints do shell.

POR QUE ELE EXISTE:
- protege o contrato visual e navegacional dos hints usados no compass compartilhado.

O QUE ESTE ARQUIVO FAZ:
1. testa a unidade que monta os tres hints principais.
2. valida em paginas reais se preview, hint copy e destino continuam consistentes.

PONTOS CRITICOS:
- se estes testes quebrarem, o shell pode continuar renderizando sem erros aparentes, mas perder legibilidade ou levar o usuario para um destino quebrado.
"""

from html.parser import HTMLParser
from pathlib import Path
from unittest import TestCase as UnitTestCase

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from finance.models import Enrollment, MembershipPlan, Payment, PaymentStatus
from onboarding.models import IntakeStatus, StudentIntake
from students.models import Student


class PulseChipContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.chips = []
        self.current_chip = None
        self.current_field = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        class_names = attributes.get('class', '').split()
        element_id = attributes.get('id')

        if element_id:
            self.ids.add(element_id)

        if tag == 'a' and 'pulse-chip' in class_names:
            self.current_chip = {
                'classes': class_names,
                'href': attributes.get('href', ''),
                'aria_label': attributes.get('aria-label', ''),
                'label': '',
                'number': '',
                'hint_copy': '',
            }
            self.current_field = None
            return

        if self.current_chip is None or tag != 'span':
            return

        if 'pulse-label' in class_names:
            self.current_field = 'label'
        elif 'pulse-number' in class_names:
            self.current_field = 'number'
        elif 'pulse-hint-copy' in class_names:
            self.current_field = 'hint_copy'

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_chip is not None:
            self.chips.append(self.current_chip)
            self.current_chip = None
            self.current_field = None
            return

        if tag == 'span':
            self.current_field = None

    def handle_data(self, data):
        if self.current_chip is None or self.current_field is None:
            return

        text = data.strip()
        if not text:
            return

        current_value = self.current_chip[self.current_field]
        self.current_chip[self.current_field] = f'{current_value} {text}'.strip()


class TopbarAlertParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alerts = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return

        attributes = dict(attrs)
        ui_key = attributes.get('data-ui')
        if ui_key not in {'topbar-finance-alert', 'topbar-intake-alert'}:
            return

        self.alerts[ui_key] = attributes


class ShellActionHrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return

        attributes = dict(attrs)
        class_names = attributes.get('class', '').split()
        if 'pulse-chip' in class_names:
            self.hrefs.append(attributes.get('href', ''))


class ShellHintBuilderUnitTests(UnitTestCase):
    def test_build_shell_action_buttons_from_focus_preserves_hint_contract(self):
        buttons = build_shell_action_buttons_from_focus(
            focus=[
                {'target_label': 'Abrir a fila mais quente', 'count': 4, 'href': '#priority-board'},
                {'target_label': 'Ver o que ainda esta em aberto', 'count': 0, 'href': '#pending-board'},
            ],
            next_action={'target_label': 'Fechar o proximo passo do dia', 'href': '#next-board'},
            scope='finance',
        )

        self.assertEqual(len(buttons), 3)
        self.assertEqual(
            buttons,
            [
                {
                    'kind': 'priority',
                    'label': 'Prioridade',
                    'count': 4,
                    'target_label': 'Abrir a fila mais quente',
                    'href': '#priority-board',
                },
                {
                    'kind': 'pending',
                    'label': 'Pendente',
                    'count': None,
                    'target_label': 'Ver o que ainda esta em aberto',
                    'href': '#pending-board',
                },
                {
                    'kind': 'next-action',
                    'label': 'Proximo',
                    'count': None,
                    'target_label': 'Fechar o proximo passo do dia',
                    'href': '#next-board',
                },
            ],
        )

    def test_shared_hint_css_preserves_balloon_visibility_contract(self):
        compass_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'compass.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.pulse-chip {', compass_css)
        self.assertIn('.pulse-label {', compass_css)
        self.assertIn('.pulse-number {', compass_css)
        self.assertIn('.pulse-priority {', compass_css)
        self.assertIn('.pulse-pending {', compass_css)
        self.assertIn('.pulse-next-action {', compass_css)
        self.assertIn('.compass-eyebrow-pill {', compass_css)
        self.assertIn('.page-compass-context {', compass_css)
        self.assertIn('border-radius: 999px;', compass_css)
        self.assertIn('text-transform: uppercase;', compass_css)
        self.assertIn('.pulse-chip:hover', compass_css)
        self.assertIn('.pulse-chip:focus-visible', compass_css)

    def test_shell_js_preserves_celebration_contract_for_count_drop_to_zero(self):
        shell_js = (Path(__file__).resolve().parents[2] / 'static' / 'js' / 'core' / 'shell.js').read_text(
            encoding='utf-8'
        )

        self.assertIn('function celebrateCountDrop(kind, previousCount, currentCount) {', shell_js)
        self.assertIn('if (previousCount <= currentCount) {', shell_js)
        self.assertIn("const celebrationStorageKey = 'octobox-shell-counts:' + shellUserId;", shell_js)
        self.assertIn('function readStorage(storage, key) {', shell_js)
        self.assertIn('function writeStorage(storage, key, value) {', shell_js)
        self.assertIn("previousCounts = JSON.parse(readStorage(window.sessionStorage, celebrationStorageKey) || 'null');", shell_js)
        self.assertIn('writeStorage(window.sessionStorage, celebrationStorageKey, JSON.stringify(currentCounts));', shell_js)
        self.assertIn("celebrateCountDrop('overdue-payments', previousCounts.overduePayments || 0, currentCounts.overduePayments);", shell_js)
        self.assertIn("celebrateCountDrop('pending-intakes', previousCounts.pendingIntakes || 0, currentCounts.pendingIntakes);", shell_js)
        self.assertIn("eyebrow: 'Parabens 🎉'", shell_js)
        self.assertIn("copy: delta === 1", shell_js)
        self.assertIn("'Um vencimento saiu da pressao. Bom avanço.'", shell_js)
        self.assertIn("delta + ' vencimentos sairam da pressao. Bom avanço.'", shell_js)
        self.assertIn("eyebrow: 'Boa 👏'", shell_js)
        self.assertIn("'Um intake saiu da fila. Bom avanço.'", shell_js)
        self.assertIn("delta + ' intakes sairam da fila. Bom avanço.'", shell_js)

    def test_shell_theme_toggle_preserves_visual_state_contract(self):
        shell_js = (Path(__file__).resolve().parents[2] / 'static' / 'js' / 'core' / 'shell.js').read_text(
            encoding='utf-8'
        )
        topbar_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'topbar.css'
        ).read_text(encoding='utf-8')
        base_html = (Path(__file__).resolve().parents[2] / 'templates' / 'layouts' / 'base.html').read_text(
            encoding='utf-8'
        )

        self.assertIn('theme-toggle-icon', base_html)
        self.assertIn('theme-toggle-label', base_html)
        self.assertIn('topbar-manifesto', base_html)
        self.assertIn('Produto vivo. Controle legivel. Acao imediata.', base_html)
        self.assertIn('visually-hidden', base_html)
        self.assertIn("themeToggle.setAttribute('data-theme-state', isDark ? 'dark' : 'light');", shell_js)
        self.assertIn("var themeIcon = isDark ? '☾' : '☼';", shell_js)
        self.assertIn("var themeLabel = isDark ? 'Escuro' : 'Claro';", shell_js)
        self.assertIn('.theme-toggle[data-theme-state="light"] {', topbar_css)
        self.assertIn('.theme-toggle[data-theme-state="dark"] {', topbar_css)
        self.assertIn('.theme-toggle-icon {', topbar_css)
        self.assertIn('.topbar-manifesto {', topbar_css)

    def test_compass_and_hero_css_preserve_two_line_reading_rule(self):
        compass_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'compass.css'
        ).read_text(encoding='utf-8')
        operations_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'operations' / 'core.css'
        ).read_text(encoding='utf-8')
        operations_refinements_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'operations' / 'refinements' / 'hero.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.page-compass-title {', compass_css)
        self.assertIn('.operation-hero-copy {', operations_css)
        self.assertIn('.operation-hero-main h2 {', operations_css)
        self.assertIn('.operation-hero-panel .operation-card-copy {', operations_css)
        self.assertIn('-webkit-line-clamp: 2;', operations_css)
        self.assertIn('.operation-hero:has(.operation-hero-side),', operations_refinements_css)
        self.assertIn('.operation-hero:has(> .operation-hero-panel) {', operations_refinements_css)

    def test_topbar_css_preserves_warning_danger_and_zero_state_contract(self):
        topbar_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'topbar.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.alert-chip.has-volume {', topbar_css)
        self.assertIn('color: #92400e;', topbar_css)
        self.assertIn('rgba(245, 158, 11, 0.18)', topbar_css)
        self.assertIn('.alert-chip.danger.has-volume {', topbar_css)
        self.assertIn('color: #991b1b;', topbar_css)
        self.assertIn('.alert-chip.is-zero {', topbar_css)
        self.assertIn('.alert-chip.is-zero .alert-dot,', topbar_css)
        self.assertIn('.alert-chip.danger.is-zero .alert-dot {', topbar_css)
        self.assertIn('display: none;', topbar_css)
        self.assertNotIn('top: 10px;', topbar_css)

    def test_shell_topbar_does_not_force_scroll_to_top(self):
        shell_js = (Path(__file__).resolve().parents[2] / 'static' / 'js' / 'core' / 'shell.js').read_text(
            encoding='utf-8'
        )

        self.assertNotIn('function shouldIgnoreTopbarScrollClick(target) {', shell_js)
        self.assertNotIn('function scrollPageToTop() {', shell_js)
        self.assertNotIn("topbar.addEventListener('click'", shell_js)


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
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=1),
            amount='289.90',
            status=PaymentStatus.OVERDUE,
        )
        StudentIntake.objects.create(
            full_name='Lead Hint',
            phone='5511999992222',
            source='manual',
            status=IntakeStatus.NEW,
        )
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
            self.assertTrue(chip['label'], f"Chip label should not be empty: {chip}")

        for chip in parser.chips:
            self.assertTrue(chip['aria_label'])

            if chip['href'].startswith('#'):
                self.assertIn(chip['href'][1:], parser.ids)

    def test_shell_hints_render_consistent_contract_on_real_pages(self):
        self.client.force_login(self.user)

        scenarios = [
            (reverse('dashboard'), 'dashboard'),
            (reverse('finance-center'), 'finance'),
            (reverse('membership-plan-quick-update', args=[self.plan.id]), 'finance-plan-form'),
        ]

        for url, expected_scope in scenarios:
            with self.subTest(url=url):
                response = self.client.get(url)
                self._assert_hint_contract(response, expected_scope=expected_scope)

    def test_topbar_alerts_stay_consistent_across_dashboard_students_and_finance(self):
        self.client.force_login(self.user)

        scenarios = [
            reverse('dashboard'),
            reverse('student-directory'),
            reverse('finance-center'),
        ]

        for url in scenarios:
            with self.subTest(url=url):
                response = self.client.get(url)
                parser = TopbarAlertParser()
                parser.feed(response.content.decode())

                finance_alert = parser.alerts['topbar-finance-alert']
                intake_alert = parser.alerts['topbar-intake-alert']

                self.assertEqual(finance_alert['href'], '/financeiro/')
                self.assertEqual(finance_alert['data-count-kind'], 'overdue-payments')
                self.assertEqual(finance_alert['data-count-value'], '1')
                self.assertIn('1 vencimento', finance_alert['aria-label'])

                self.assertEqual(intake_alert['href'], '/entradas/')
                self.assertEqual(intake_alert['data-count-kind'], 'pending-intakes')
                self.assertEqual(intake_alert['data-count-value'], '1')
                self.assertIn('1 entrada pendente', intake_alert['aria-label'])

    def test_dashboard_and_finance_point_intake_communication_to_the_new_center(self):
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse('dashboard'))
        finance_response = self.client.get(reverse('finance-center'))
        intake_response = self.client.get(reverse('intake-center'))
        students_response = self.client.get(reverse('student-directory'))

        self.assertContains(dashboard_response, 'href="/entradas/#intake-queue-board"')
        self.assertContains(finance_response, 'href="/entradas/"')
        self.assertContains(intake_response, 'id="intake-queue-board"')
        self.assertContains(students_response, 'id="student-intake-board"')
        self.assertContains(students_response, 'href="/entradas/#intake-queue-board"')

    def test_reception_dashboard_and_workspace_share_operational_intake_and_payment_targets(self):
        self.client.force_login(self.reception)

        dashboard_response = self.client.get(reverse('dashboard'))
        reception_response = self.client.get(reverse('reception-workspace'))
        students_response = self.client.get(reverse('student-directory'))

        dashboard_parser = ShellActionHrefParser()
        dashboard_parser.feed(dashboard_response.content.decode())

        reception_parser = ShellActionHrefParser()
        reception_parser.feed(reception_response.content.decode())

        self.assertIn('/operacao/recepcao/#reception-payment-board', dashboard_parser.hrefs)
        self.assertIn('/operacao/recepcao/#reception-intake-board', dashboard_parser.hrefs)
        self.assertIn('#reception-intake-board', reception_parser.hrefs)
        self.assertIn('#reception-payment-board', reception_parser.hrefs)

        topbar_parser = TopbarAlertParser()
        topbar_parser.feed(dashboard_response.content.decode())
        self.assertEqual(topbar_parser.alerts['topbar-finance-alert']['href'], '/operacao/recepcao/#reception-payment-board')
        self.assertEqual(topbar_parser.alerts['topbar-intake-alert']['href'], '/entradas/')

        self.assertContains(reception_response, 'id="reception-intake-board"')
        self.assertContains(reception_response, 'id="reception-payment-board"')
        self.assertContains(students_response, 'id="student-intake-board"')
        self.assertContains(students_response, 'href="/entradas/#intake-queue-board"')