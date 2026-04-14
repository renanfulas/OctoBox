"""
ARQUIVO: testes da fronteira inicial de API.

POR QUE ELE EXISTE:
- Garante que a entrada versionada da API continue estavel enquanto o produto cresce.

O QUE ESTE ARQUIVO FAZ:
1. Testa o indice da API.
2. Testa o manifesto da v1.
3. Testa a rota de saude da v1.

PONTOS CRITICOS:
- Essas rotas viram contrato para mobile e integracoes futuras.
"""

import json
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from finance.models import Enrollment, MembershipPlan, Payment, PaymentStatus
from students.models import Student


class ApiFoundationTests(TestCase):
    def test_api_root_exposes_available_versions(self):
        response = self.client.get(reverse("api-root"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["kind"], "api-root")
        self.assertIn("v1", response.json()["available_versions"])

    def test_api_v1_manifest_exposes_health_resource(self):
        response = self.client.get(reverse("api-v1-manifest"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "v1")
        self.assertEqual(response.json()["resources"]["health"], "/api/v1/health/")

    def test_api_v1_health_reports_ok(self):
        response = self.client.get(reverse("api-v1-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["api_boundary"], "stable-entrypoint")

    def test_api_v1_health_exposes_runtime_boundary(self):
        with patch.dict(os.environ, {"BOX_RUNTIME_SLUG": "box-piloto-centro"}, clear=False):
            response = self.client.get(reverse("api-v1-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["runtime_slug"], "box-piloto-centro")
        self.assertEqual(response.json()["runtime_namespace"], "octobox:box-piloto-centro")


class ApiFinanceSurfaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="api-owner",
            email="api-owner@example.com",
            password="senha-forte-123",
        )
        self.client.force_login(self.user)
        self.student = Student.objects.create(full_name="Bruna Freeze", phone="5511999999999")
        self.plan = MembershipPlan.objects.create(name="Cross Prime", price="289.90")
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        self.pending_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            amount="289.90",
            status=PaymentStatus.PENDING,
        )
        self.paid_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=30),
            amount="289.90",
            status=PaymentStatus.PAID,
        )

    def test_freeze_student_returns_updated_financial_fragments(self):
        response = self.client.post(
            reverse("api-v1-finance-freeze"),
            data=json.dumps({"student_id": self.student.id, "days": 10}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertIn("fragments", body)
        self.assertIn("student-financial-id-card", body["fragments"]["id_card"])
        self.assertIn("student-financial-kpi-card", body["fragments"]["kpis"])
        self.assertIn("student-financial-ledger", body["fragments"]["ledger"])
        self.assertIn("student-payment-management-root", body["fragments"]["management"])
        self.assertIn("student-payment-checkout-form", body["fragments"]["checkout"])
        self.assertIn("student-enrollment-management", body["fragments"]["enrollment"])

        self.pending_payment.refresh_from_db()
        self.assertEqual(
            self.pending_payment.due_date,
            timezone.localdate() + timezone.timedelta(days=10),
        )
        self.assertIn("289", body["fragments"]["id_card"])
        self.assertIn("579", body["fragments"]["kpis"])
