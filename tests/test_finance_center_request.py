"""
ARQUIVO: teste de request autenticado da central financeira.

POR QUE ELE EXISTE:
- protege a subida da tela financeira principal, hoje critica e fortemente dependente de snapshot agregado.

O QUE ESTE ARQUIVO FAZ:
1. cria um usuario com papel autorizado.
2. monta um minimo de dados financeiros reais.
3. garante que o GET da central financeira responde 200 sem traceback.

PONTOS CRITICOS:
- se este teste falhar, a central financeira pode ter quebrado em queries, presenter ou template.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_OWNER
from catalog.finance_queries import build_finance_snapshot
from finance.models import Payment, PaymentStatus
from students.models import Student


class FinanceCenterRequestTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles")
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="finance-owner",
            email="finance-owner@example.com",
            password="test",
        )
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))

    def test_authenticated_finance_center_request_returns_ok(self):
        today = timezone.localdate()
        student = Student.objects.create(
            full_name="Aluno Financeiro",
            phone="+5511999990002",
        )
        Payment.objects.create(
            student=student,
            due_date=today - timedelta(days=2),
            amount=Decimal("199.90"),
            status=PaymentStatus.PENDING,
        )

        self.client.force_login(self.owner)

        response = self.client.get(reverse("finance-center"))

        self.assertEqual(response.status_code, 200)

    def test_finance_transport_payload_is_json_serializable(self):
        today = timezone.localdate()
        student = Student.objects.create(
            full_name="Aluno Transporte Financeiro",
            phone="+5511999990003",
        )
        Payment.objects.create(
            student=student,
            due_date=today - timedelta(days=3),
            amount=Decimal("249.90"),
            status=PaymentStatus.PENDING,
        )

        snapshot = build_finance_snapshot()
        transport_payload = snapshot["transport_payload"]
        encoded = json.dumps(transport_payload, cls=DjangoJSONEncoder)

        self.assertIsInstance(transport_payload["financial_alerts"], list)
        self.assertIsInstance(transport_payload["recent_movements"], list)
        self.assertEqual(transport_payload["financial_alerts"][0]["student_full_name"], "Aluno Transporte Financeiro")
        self.assertIn('"financial_alerts"', encoded)
