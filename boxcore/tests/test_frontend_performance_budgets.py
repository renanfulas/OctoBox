"""
ARQUIVO: budgets automatizados de performance front-end.

POR QUE ELE EXISTE:
- transforma as sprints de performance em contratos que falham cedo.
- protege o caminho inicial contra retorno de fonte externa, scripts globais diretos e CSS critico amplo demais.

O QUE ESTE ARQUIVO FAZ:
1. valida o HTML inicial da tela de alunos.
2. valida o budget de scripts globais progressivos.
3. valida o budget de CSS critico da tela de alunos.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.presentation.student_directory_page import build_student_directory_page
from finance.models import Enrollment, MembershipPlan, Payment
from shared_support.static_assets import resolve_runtime_css_paths
from students.models import Student


class FrontendPerformanceBudgetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='performance-owner',
            email='performance-owner@example.com',
            password='senha-forte-123',
        )
        self.student = Student.objects.create(full_name='Bruna Costa', phone='5511988888888')
        self.plan = MembershipPlan.objects.create(name='Cross Prime', price='289.90')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            amount='289.90',
        )

    def test_student_directory_initial_html_respects_global_script_budget(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('fonts/manrope/manrope-latin-variable.woff2', html)
        self.assertIn('as="font"', html)
        self.assertIn('type="font/woff2"', html)
        self.assertIn('crossorigin', html)
        self.assertNotIn('fonts.googleapis.com', html)
        self.assertNotIn('fonts.gstatic.com', html)
        self.assertIn('js/core/search-loader.js', html)
        self.assertNotIn('js/core/search.js', html)
        self.assertIn('js/core/dynamic-visuals-loader.js', html)
        self.assertNotIn('js/core/dynamic-visuals.js', html)
        self.assertIn('js/core/shell-effects-loader.js', html)
        self.assertNotIn('js/core/shell-effects.js', html)

    def test_typography_tokens_use_premium_stack_without_external_import(self):
        tokens = (settings.BASE_DIR / 'static' / 'css' / 'design-system' / 'tokens.css').read_text(encoding='utf-8')

        self.assertIn('--font-body: "Manrope", system-ui, sans-serif;', tokens)
        self.assertIn('--font-display: "Object Sans", "Manrope", system-ui, sans-serif;', tokens)
        self.assertIn('font-family: "Manrope";', tokens)
        self.assertIn('font-weight: 400 800;', tokens)
        self.assertIn('font-display: swap;', tokens)
        self.assertIn('url("../../fonts/manrope/manrope-latin-variable.woff2") format("woff2")', tokens)
        self.assertIn(
            '--font-display-critical: "Aptos Display", "Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif;',
            tokens,
        )
        self.assertNotIn('fonts.googleapis.com', tokens)
        self.assertNotIn('fonts.gstatic.com', tokens)
        self.assertNotIn('@import url("https://', tokens)

    def test_local_manrope_font_stays_small_enough_for_critical_preload(self):
        font_path = settings.BASE_DIR / 'static' / 'fonts' / 'manrope' / 'manrope-latin-variable.woff2'

        self.assertTrue(font_path.exists())
        self.assertLessEqual(font_path.stat().st_size, 28 * 1024)

    def test_student_mobile_css_guards_against_off_canvas_overflow(self):
        quick_panel_css = (settings.BASE_DIR / 'static' / 'css' / 'catalog' / 'students' / 'quick-panel.css').read_text(encoding='utf-8')
        profile_menu_css = (
            settings.BASE_DIR / 'static' / 'css' / 'design-system' / 'components' / 'topbar_profile_menu.css'
        ).read_text(encoding='utf-8')
        student_responsive_css = (
            settings.BASE_DIR / 'static' / 'css' / 'catalog' / 'students' / 'responsive.css'
        ).read_text(encoding='utf-8')

        self.assertIn('transform: translateY(calc(100% + 24px));', quick_panel_css)
        self.assertIn('.student-quick-panel.is-open', quick_panel_css)
        self.assertIn('right: 0;', profile_menu_css)
        self.assertIn('transform-origin: top right;', profile_menu_css)
        self.assertIn('.student-directory-table tbody tr > td:nth-child(n)', student_responsive_css)
        self.assertIn('display: block;', student_responsive_css)

    def test_student_directory_critical_css_stays_under_budget(self):
        payload = build_student_directory_page(
            student_count=0,
            students=[],
            student_filter_form=None,
            snapshot={'interactive_kpis': []},
            current_role_slug='Owner',
            base_query_string='',
        )
        assets = payload['assets']
        critical_css_runtime = resolve_runtime_css_paths(assets['css'])
        critical_css_bytes = sum(
            (settings.BASE_DIR / 'static' / asset_path).stat().st_size
            for asset_path in critical_css_runtime
            if (settings.BASE_DIR / 'static' / asset_path).exists()
        )

        self.assertLessEqual(len(critical_css_runtime), 9)
        self.assertLessEqual(critical_css_bytes, 56 * 1024)
        self.assertIn('css/catalog/students/scene.css', critical_css_runtime)
        self.assertIn('css/catalog/students/intake-directory.css', critical_css_runtime)
        self.assertNotIn('css/catalog/shared.css', assets['css'])
        self.assertNotIn('css/catalog/students.css', assets['css'])
        self.assertNotIn('css/catalog/students/quick-panel.css', critical_css_runtime)
        self.assertEqual(assets['enhancement_css'], ['bundle:css/catalog/students-enhancement.css'])
        self.assertEqual(assets['deferred_css'], ['bundle:css/catalog/students-deferred.css'])

    def test_student_directory_progressive_css_groups_have_runtime_budget(self):
        payload = build_student_directory_page(
            student_count=0,
            students=[],
            student_filter_form=None,
            snapshot={'interactive_kpis': []},
            current_role_slug='Owner',
            base_query_string='',
        )
        assets = payload['assets']
        deferred_css_runtime = resolve_runtime_css_paths(assets['deferred_css'])
        enhancement_css_runtime = resolve_runtime_css_paths(assets['enhancement_css'])

        self.assertEqual(deferred_css_runtime, ['css/catalog/students-deferred.css'])
        self.assertEqual(enhancement_css_runtime, ['css/catalog/students-enhancement.css'])
        self.assertIn('@import url("./students/focus-priority.css");', (settings.BASE_DIR / 'static' / deferred_css_runtime[0]).read_text(encoding='utf-8'))
        self.assertIn('@import url("./students/quick-panel.css");', (settings.BASE_DIR / 'static' / enhancement_css_runtime[0]).read_text(encoding='utf-8'))

    def test_finance_center_initial_html_uses_progressive_asset_contract(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('fonts/manrope/manrope-latin-variable.woff2', html)
        self.assertIn('as="font"', html)
        self.assertNotIn('fonts.googleapis.com', html)
        self.assertNotIn('fonts.gstatic.com', html)
        self.assertIn('css/catalog/finance/_shell.css', html)
        self.assertNotIn('css/catalog/finance.css', html)
        self.assertIn('css/catalog/finance-deferred.css', html)
        self.assertIn('css/catalog/finance-enhancement.css', html)
        self.assertIn('defer src="/static/js/pages/finance/finance-priority-carousel.js', html)
        self.assertNotIn('<script src="/static/js/pages/finance/finance-priority-carousel.js', html)

    def test_finance_center_critical_css_stays_under_budget(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))
        assets = response.context['current_page_assets']
        critical_css_runtime = assets['css_runtime']
        critical_css_bytes = sum(
            (settings.BASE_DIR / 'static' / asset_path).stat().st_size
            for asset_path in critical_css_runtime
            if (settings.BASE_DIR / 'static' / asset_path).exists()
        )

        self.assertLessEqual(len(critical_css_runtime), 9)
        self.assertLessEqual(critical_css_bytes, 48 * 1024)
        self.assertIn('css/catalog/finance/_shell.css', critical_css_runtime)
        self.assertIn('css/catalog/finance/_metrics.css', critical_css_runtime)
        self.assertNotIn('css/catalog/finance.css', assets['css'])
        self.assertNotIn('css/catalog/finance/_boards.css', critical_css_runtime)
        self.assertNotIn('css/design-system/financial.css', critical_css_runtime)
        self.assertEqual(assets['deferred_css'], ['bundle:css/catalog/finance-deferred.css'])
        self.assertEqual(assets['enhancement_css'], ['bundle:css/catalog/finance-enhancement.css'])

    def test_finance_center_progressive_css_groups_have_runtime_budget(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))
        assets = response.context['current_page_assets']
        deferred_css_runtime = assets['deferred_css_runtime']
        enhancement_css_runtime = assets['enhancement_css_runtime']

        self.assertEqual(deferred_css_runtime, ['css/catalog/finance-deferred.css'])
        self.assertEqual(enhancement_css_runtime, ['css/catalog/finance-enhancement.css'])
        self.assertIn(
            '@import url("./finance/_boards.css");',
            (settings.BASE_DIR / 'static' / deferred_css_runtime[0]).read_text(encoding='utf-8'),
        )
        self.assertIn(
            '@import url("./finance/_plan-page.css");',
            (settings.BASE_DIR / 'static' / deferred_css_runtime[0]).read_text(encoding='utf-8'),
        )
        self.assertIn(
            '@import url("./finance/_signature.css");',
            (settings.BASE_DIR / 'static' / enhancement_css_runtime[0]).read_text(encoding='utf-8'),
        )

    def test_finance_center_page_scripts_are_deferred(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('finance-center'))

        self.assertEqual(
            response.context['current_page_assets']['deferred_js'],
            [
                'js/pages/interactive_tabs.js',
                'js/pages/finance/finance-filter-summary.js',
                'js/pages/finance/finance-mode-controller.js',
                'js/pages/finance/finance-trend-board-controller.js',
                'js/pages/finance/finance-priority-carousel.js',
            ],
        )
