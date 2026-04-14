"""
ARQUIVO: teste de serializacao do snapshot do dashboard.

POR QUE ELE EXISTE:
- protege o contrato JSON-first do snapshot principal do dashboard.

O QUE ESTE ARQUIVO FAZ:
1. monta um snapshot real do dashboard com dados operacionais.
2. garante que o payload pode ser serializado com DjangoJSONEncoder.
3. impede regressao em que QuerySet ou Model cru escapem para o cache.

PONTOS CRITICOS:
- se este teste falhar, o dashboard pode voltar a quebrar ao salvar no cache compartilhado.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.utils import timezone

from dashboard.dashboard_snapshot_queries import build_dashboard_snapshot
from finance.models import Payment, PaymentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession
from students.models import Student


class DashboardSnapshotSerializationTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.coach = user_model.objects.create_user(
            username="dashboard-serialization-coach",
            email="dashboard-serialization@example.com",
            password="senha-forte-123",
        )

    def test_dashboard_snapshot_is_json_serializable(self):
        today = timezone.localdate()
        now = timezone.now()

        student = Student.objects.create(
            full_name="Aluno Snapshot",
            phone="+5511999990001",
        )
        Payment.objects.create(
            student=student,
            due_date=today - timedelta(days=1),
            amount=Decimal("289.90"),
            status=PaymentStatus.PENDING,
        )
        absence_session = ClassSession.objects.create(
            title="Turma que gerou falta",
            coach=self.coach,
            scheduled_at=now - timedelta(days=1),
            duration_minutes=60,
            capacity=12,
        )
        Attendance.objects.create(
            student=student,
            session=absence_session,
            status=AttendanceStatus.ABSENT,
        )
        ClassSession.objects.create(
            title="Turma futura",
            coach=self.coach,
            scheduled_at=now + timedelta(hours=2),
            duration_minutes=60,
            capacity=15,
        )

        snapshot = build_dashboard_snapshot(
            today=today,
            month_start=today.replace(day=1),
            role_slug="owner",
        )

        encoded = json.dumps(snapshot, cls=DjangoJSONEncoder)

        self.assertIsInstance(snapshot["student_health"], list)
        self.assertIsInstance(snapshot["payment_alerts"], list)
        self.assertIsInstance(snapshot["next_actionable_payment_alert"], dict)
        self.assertEqual(snapshot["payment_alerts"][0]["student_full_name"], "Aluno Snapshot")
        self.assertEqual(snapshot["upcoming_sessions"][0]["title"], "Turma futura")
        self.assertIn('"student_health"', encoded)
