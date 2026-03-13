"""
ARQUIVO: testes do dashboard.

POR QUE ELE EXISTE:
- Garante que o painel principal continue acessível e renderizando o básico.

O QUE ESTE ARQUIVO FAZ:
1. Testa proteção por login.
2. Testa renderização do painel autenticado.

PONTOS CRITICOS:
- Se esses testes falharem, pode ter quebrado rota, template ou contexto do dashboard.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from finance.models import MembershipPlan
from operations.models import Attendance, ClassSession, SessionStatus
from students.models import Student


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='gestor',
            email='gestor@example.com',
            password='senha-forte-123',
        )
        MembershipPlan.objects.create(name='Mensal 3x', price='249.90')
        Student.objects.create(full_name='Ana Silva', phone='5511999999999')

    def test_redirects_when_user_is_not_authenticated(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operação do box em um painel só.')
        self.assertContains(response, 'Owner')

    def test_dashboard_marks_today_session_as_in_progress_during_runtime(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 08h',
            coach=self.user,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            capacity=10,
            status=SessionStatus.SCHEDULED,
        )
        Attendance.objects.create(student=Student.objects.create(full_name='Aluno 08h', phone='5511988880001'), session=session)
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.dashboard.dashboard_snapshot_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Em andamento')
        self.assertContains(response, '1/10')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.SCHEDULED)

    def test_dashboard_auto_completes_session_after_end_time(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 08h final',
            coach=self.user,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('08:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            capacity=12,
            status=SessionStatus.SCHEDULED,
        )
        Attendance.objects.create(student=Student.objects.create(full_name='Aluno final', phone='5511988880002'), session=session)
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('09:01', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.dashboard.dashboard_snapshot_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Finalizada')
        self.assertContains(response, '1/12')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)