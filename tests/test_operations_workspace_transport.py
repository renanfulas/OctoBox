"""
ARQUIVO: testes de blindagem dos workspaces de operations.

POR QUE ELE EXISTE:
- protege os workspaces mais criticos enquanto a camada de operations separa server payload de transport payload.

O QUE ESTE ARQUIVO FAZ:
1. garante que manager e recepcao sobem com GET autenticado.
2. valida que os transport payloads sao JSON-serializable.

PONTOS CRITICOS:
- se estes testes falharem, a tela pode ter voltado a depender de ORM cru dentro do envelope de leitura.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_RECEPTION
from communications.models import WhatsAppContact, WhatsAppContactStatus
from finance.models import Payment, PaymentStatus
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from operations.models import Attendance, AttendanceStatus, ClassSession
from operations.queries import build_manager_workspace_snapshot, build_reception_workspace_snapshot
from students.models import Student


@override_settings(OPERATIONS_MANAGER_WORKSPACE_ENABLED=True)
class OperationsWorkspaceTransportTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles")
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="ops-manager",
            email="ops-manager@example.com",
            password="test",
        )
        self.reception = user_model.objects.create_user(
            username="ops-reception",
            email="ops-reception@example.com",
            password="test",
        )
        self.manager.groups.add(Group.objects.get(name=ROLE_MANAGER))
        self.reception.groups.add(Group.objects.get(name=ROLE_RECEPTION))

    def _build_operations_fixture(self):
        now = timezone.now()
        today = timezone.localdate()
        student = Student.objects.create(
            full_name="Aluno Operacional",
            phone="+5511999990101",
        )
        StudentIntake.objects.create(
            full_name="Lead Operacional",
            phone="+5511999990102",
            email="lead-operacional@example.com",
            source=IntakeSource.WHATSAPP,
            status=IntakeStatus.NEW,
        )
        WhatsAppContact.objects.create(
            phone="+5511999990103",
            display_name="Contato Solto",
            status=WhatsAppContactStatus.NEW,
        )
        Payment.objects.create(
            student=student,
            due_date=today - timedelta(days=2),
            amount=Decimal("189.90"),
            status=PaymentStatus.PENDING,
        )
        session = ClassSession.objects.create(
            title="Turma Operacional",
            scheduled_at=now + timedelta(hours=2),
            duration_minutes=60,
            capacity=12,
        )
        Attendance.objects.create(
            student=student,
            session=session,
            status=AttendanceStatus.BOOKED,
            notes="Chegar 10 min antes.",
        )
        return today

    def test_manager_workspace_request_and_transport_payload_are_safe(self):
        self._build_operations_fixture()
        self.client.force_login(self.manager)

        response = self.client.get(reverse("manager-workspace"))
        snapshot = build_manager_workspace_snapshot(actor=self.manager)
        transport_payload = snapshot["transport_payload"]
        encoded = json.dumps(transport_payload, cls=DjangoJSONEncoder)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(transport_payload["pending_intakes"], list)
        self.assertIsInstance(transport_payload["financial_alerts"], list)
        self.assertEqual(transport_payload["pending_intakes"][0]["full_name"], "Lead Operacional")
        self.assertEqual(transport_payload["financial_alerts"][0]["student_full_name"], "Aluno Operacional")
        self.assertIn('"financial_alerts"', encoded)

    def test_reception_workspace_request_and_transport_payload_are_safe(self):
        today = self._build_operations_fixture()
        self.client.force_login(self.reception)

        response = self.client.get(reverse("reception-workspace"))
        snapshot = build_reception_workspace_snapshot(today=today)
        transport_payload = snapshot["transport_payload"]
        encoded = json.dumps(transport_payload, cls=DjangoJSONEncoder)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(transport_payload["reception_intakes"], list)
        self.assertIsInstance(transport_payload["reception_sessions"], list)
        self.assertEqual(transport_payload["reception_intakes"][0]["full_name"], "Lead Operacional")
        self.assertEqual(transport_payload["reception_sessions"][0]["title"], "Turma Operacional")
        self.assertIn('"reception_sessions"', encoded)
