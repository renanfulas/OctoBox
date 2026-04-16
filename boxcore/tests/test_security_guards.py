"""
ARQUIVO: testes dos guardas transversais de seguranca.

POR QUE ELE EXISTE:
- protege o endurecimento minimo de login, admin e rotas sensiveis contra regressao.

O QUE ESTE ARQUIVO FAZ:
1. garante que o admin nao fique publicado em /admin/.
2. garante que o login bloqueie rajadas curtas por repeticao.
3. garante que exportacoes e autocomplete sofram throttle por escopo.
4. garante que IP ou faixa bloqueada parem no middleware.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_MANAGER
from finance.models import Enrollment, MembershipPlan, Payment
from students.models import Student


class SecurityGuardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(
            username='security-owner',
            email='security-owner@example.com',
            password='senha-forte-123',
        )
        self.student = Student.objects.create(full_name='Seguranca Teste', phone='5511999990000')
        self.plan = MembershipPlan.objects.create(name='Plano Seguranca', price='199.90')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            amount='199.90',
        )

    def test_default_admin_route_is_not_public(self):
        default_response = self.client.get('/admin/')
        hardened_admin_response = self.client.get(f'/{settings.ADMIN_URL_PATH}')

        self.assertEqual(default_response.status_code, 404)
        self.assertIn(hardened_admin_response.status_code, (200, 302))

    def test_staff_without_owner_or_dev_role_cannot_enter_hardened_admin(self):
        manager = get_user_model().objects.create_user(
            username='security-manager',
            email='security-manager@example.com',
            password='senha-forte-123',
            is_staff=True,
        )
        manager.groups.add(Group.objects.create(name=ROLE_MANAGER))
        self.client.force_login(manager)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)

    def test_superuser_without_bootstrapped_role_can_enter_hardened_admin(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)

    def test_csp_does_not_allow_external_font_hosts(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))

        self.assertIn('Content-Security-Policy', response)
        csp_policy = response['Content-Security-Policy']
        self.assertIn("font-src 'self'", csp_policy)
        self.assertNotIn('fonts.googleapis.com', csp_policy)
        self.assertNotIn('fonts.gstatic.com', csp_policy)

    @override_settings(LOGIN_RATE_LIMIT_MAX_REQUESTS=2, LOGIN_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_login_blocks_short_burst_attempts(self):
        payload = {
            'username': 'intruso',
            'password': 'senha-errada',
        }

        first_response = self.client.post(reverse('login'), data=payload)
        second_response = self.client.post(reverse('login'), data=payload)
        blocked_response = self.client.post(reverse('login'), data=payload)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    @override_settings(EXPORT_RATE_LIMIT_MAX_REQUESTS=1, EXPORT_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_student_export_blocks_short_burst_attempts(self):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse('student-directory-export', args=['csv']))
        blocked_response = self.client.get(reverse('student-directory-export', args=['csv']))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    @override_settings(EXPORT_RATE_LIMIT_MAX_REQUESTS=1, EXPORT_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_finance_export_blocks_short_burst_attempts(self):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse('finance-report-export', args=['csv']))
        blocked_response = self.client.get(reverse('finance-report-export', args=['csv']))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    @override_settings(AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS=1, AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS=60)
    def test_student_autocomplete_blocks_short_burst_attempts(self):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse('api-v1-student-autocomplete'), {'q': 'Seguranca'})
        blocked_response = self.client.get(reverse('api-v1-student-autocomplete'), {'q': 'Seguranca'})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    @override_settings(ANTI_EXFILTRATION_MAX_REQUESTS=1, ANTI_EXFILTRATION_WINDOW_SECONDS=60)
    def test_student_profile_read_blocks_short_burst_attempts(self):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse('student-quick-update', args=[self.student.id]))
        blocked_response = self.client.get(reverse('student-quick-update', args=[self.student.id]))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response['Retry-After'], '60')

    @override_settings(ANTI_EXFILTRATION_MAX_REQUESTS=1, ANTI_EXFILTRATION_WINDOW_SECONDS=60)
    def test_student_internal_read_endpoints_do_not_consume_profile_quota(self):
        self.client.force_login(self.user)

        snapshot_response = self.client.get(reverse('student-read-snapshot', args=[self.student.id]))
        fragments_response = self.client.get(reverse('student-drawer-fragments', args=[self.student.id]))
        status_response = self.client.get(reverse('student-lock-status', args=[self.student.id]))
        profile_response = self.client.get(reverse('student-quick-update', args=[self.student.id]))

        self.assertEqual(snapshot_response.status_code, 200)
        self.assertEqual(fragments_response.status_code, 200)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(profile_response.status_code, 200)

    @override_settings(SECURITY_BLOCKED_IP_RANGES=['10.10.0.0/16'])
    def test_blocked_ip_range_stops_request_before_view(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'), REMOTE_ADDR='10.10.3.4')

        self.assertEqual(response.status_code, 403)
