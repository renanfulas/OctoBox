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
                {'summary': 'Abrir a fila mais quente.', 'count': 4, 'href': '#priority-board'},
                {'summary': 'Ler o que ainda esta em aberto.', 'count': 0, 'href': '#pending-board'},
            ],
            next_action={'summary': 'Fechar o proximo passo do dia.', 'href': '#next-board'},
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
                    'summary': 'Abrir a fila mais quente.',
                    'href': '#priority-board',
                },
                {
                    'kind': 'pending',
                    'label': 'Pendente',
                    'count': None,
                    'summary': 'Ler o que ainda esta em aberto.',
                    'href': '#pending-board',
                },
                {
                    'kind': 'next-action',
                    'label': 'Próxima ação',
                    'count': None,
                    'summary': 'Fechar o proximo passo do dia.',
                    'href': '#next-board',
                },
            ],
        )

    def test_shared_hint_css_preserves_balloon_visibility_contract(self):
        compass_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'compass.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.pulse-hint {', compass_css)
        self.assertIn('bottom: calc(100% + 8px);', compass_css)
        self.assertIn('opacity: 0;', compass_css)
        self.assertIn('pointer-events: none;', compass_css)
        self.assertIn('overflow: visible;', compass_css)
        self.assertIn('.pulse-chip:hover .pulse-hint,', compass_css)
        self.assertIn('.pulse-chip:focus-visible .pulse-hint {', compass_css)
        self.assertIn('opacity: 1;', compass_css)
        self.assertIn('pointer-events: auto;', compass_css)
        self.assertIn('@media (hover: none), (pointer: coarse) {', compass_css)
        self.assertIn('.pulse-hint-copy {', compass_css)
        self.assertIn('white-space: normal;', compass_css)

    def test_shell_js_preserves_celebration_contract_for_count_drop_to_zero(self):
        shell_js = (Path(__file__).resolve().parents[2] / 'static' / 'js' / 'core' / 'shell.js').read_text(
            encoding='utf-8'
        )

        self.assertIn('function celebrateCountDrop(kind, previousCount, currentCount) {', shell_js)
        self.assertIn('if (previousCount <= currentCount) {', shell_js)
        self.assertIn("var celebrationStorageKey = 'octobox-shell-counts:' + shellUserId;", shell_js)
        self.assertIn('sessionStorage.getItem(celebrationStorageKey)', shell_js)
        self.assertIn('sessionStorage.setItem(celebrationStorageKey, JSON.stringify(currentCounts));', shell_js)
        self.assertIn("celebrateCountDrop('overdue-payments', previousCounts.overduePayments || 0, currentCounts.overduePayments);", shell_js)
        self.assertIn("celebrateCountDrop('pending-intakes', previousCounts.pendingIntakes || 0, currentCounts.pendingIntakes);", shell_js)
        self.assertIn("eyebrow: 'Parabens 🎉'", shell_js)
        self.assertIn("copy: delta === 1", shell_js)
        self.assertIn("? 'Um vencimento saiu da pressao. Bom avanço.'", shell_js)
        self.assertIn(": delta + ' vencimentos sairam da pressao. Bom avanço.'", shell_js)
        self.assertIn("eyebrow: 'Boa 👏'", shell_js)
        self.assertIn("? 'Um intake saiu da fila. Bom avanço.'", shell_js)
        self.assertIn(": delta + ' intakes sairam da fila. Bom avanço.'", shell_js)

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
        self.assertIn('visually-hidden', base_html)
        self.assertIn("themeToggle.setAttribute('data-theme-state', isDark ? 'dark' : 'light');", shell_js)
        self.assertIn("var themeIcon = isDark ? '☾' : '☼';", shell_js)
        self.assertIn("var themeLabel = isDark ? 'Escuro' : 'Claro';", shell_js)
        self.assertIn('.theme-toggle[data-theme-state="light"] {', topbar_css)
        self.assertIn('.theme-toggle[data-theme-state="dark"] {', topbar_css)
        self.assertIn('.theme-toggle-icon {', topbar_css)

    def test_compass_and_hero_css_preserve_two_line_reading_rule(self):
        compass_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'compass.css'
        ).read_text(encoding='utf-8')
        operations_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'operations.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.page-compass-title {', compass_css)
        self.assertIn('.page-compass-copy {', compass_css)
        self.assertIn('-webkit-line-clamp: 2;', compass_css)
        self.assertIn('.operation-hero-copy {', operations_css)
        self.assertIn('.operation-hero-main h2 {', operations_css)
        self.assertIn('.operation-hero-panel .operation-card-copy {', operations_css)
        self.assertIn('-webkit-line-clamp: 2;', operations_css)

    def test_topbar_css_preserves_warning_danger_and_zero_state_contract(self):
        topbar_css = (
            Path(__file__).resolve().parents[2] / 'static' / 'css' / 'design-system' / 'topbar.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.alert-chip.has-volume {', topbar_css)
        self.assertIn('color: #854d0e;', topbar_css)
        self.assertIn('rgba(245, 158, 11, 0.12)', topbar_css)
        self.assertIn('rgba(245, 158, 11, 0.2)', topbar_css)
        self.assertIn('.alert-chip.danger.has-volume {', topbar_css)
        self.assertIn('color: #991b1b;', topbar_css)
        self.assertIn('rgba(239, 68, 68, 0.12)', topbar_css)
        self.assertIn('rgba(239, 68, 68, 0.2)', topbar_css)
        self.assertIn('.alert-chip.is-zero {', topbar_css)
        self.assertIn('color: #166534;', topbar_css)
        self.assertIn('rgba(16, 185, 129, 0.12)', topbar_css)
        self.assertIn('.alert-chip.is-zero .alert-dot,', topbar_css)
        self.assertIn('.alert-chip.danger.is-zero .alert-dot {', topbar_css)
        self.assertIn('background: #16a34a;', topbar_css)


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
            due_date=timezone.localdate(),
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
        self.assertEqual([chip['label'] for chip in parser.chips], ['Prioridade', 'Pendente', 'Próxima ação'])

        for chip in parser.chips:
            self.assertTrue(chip['hint_copy'])
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

    def test_shell_compass_stats_use_business_metrics_instead_of_topbar_duplicates(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Papel ativo')
        self.assertContains(response, 'Base ativa')
        self.assertContains(response, 'Aulas hoje')
        self.assertNotContains(response, 'Intakes abertos')
        self.assertNotContains(response, 'Vencimentos')

    def test_finance_compass_stats_use_commercial_metrics(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        self.assertContains(response, 'Papel ativo')
        self.assertContains(response, 'Alunos em atraso')
        self.assertContains(response, 'Matriculas ativas')
        self.assertNotContains(response, 'Base ativa')

    def test_student_compass_stats_use_funnel_metrics(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))

        self.assertContains(response, 'Papel ativo')
        self.assertContains(response, 'Leads abertos')
        self.assertContains(response, 'Planos ativos')
        self.assertNotContains(response, 'Aulas hoje')

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

                self.assertEqual(intake_alert['href'], '/alunos/')
                self.assertEqual(intake_alert['data-count-kind'], 'pending-intakes')
                self.assertEqual(intake_alert['data-count-value'], '1')
                self.assertIn('1 intake', intake_alert['aria-label'])

    def test_dashboard_and_finance_keep_intake_communication_pointing_to_students_anchor(self):
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse('dashboard'))
        finance_response = self.client.get(reverse('finance-center'))
        students_response = self.client.get(reverse('student-directory'))

        self.assertContains(dashboard_response, 'href="/alunos/#student-intake-board"')
        self.assertContains(finance_response, 'href="/alunos/"')
        self.assertContains(students_response, 'id="student-intake-board"')

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
        self.assertEqual(topbar_parser.alerts['topbar-intake-alert']['href'], '/alunos/')

        self.assertContains(reception_response, 'id="reception-intake-board"')
        self.assertContains(reception_response, 'id="reception-payment-board"')
        self.assertContains(students_response, 'id="student-intake-board"')