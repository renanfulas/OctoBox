"""
ARQUIVO: testes de blindagem do adaptador de compatibilidade de communications.

POR QUE ELE EXISTE:
- protege `communications.services` para que ele permaneça um adaptador fino sobre a facade publica.

O QUE ESTE ARQUIVO FAZ:
1. valida que o service encaminha ids corretos para a facade.
2. valida que helpers legados continuam seguros com entrada parcial.
3. valida que a normalizacao de atraso continua previsivel e testavel.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from communications.services import build_message_body, normalize_payment_status, register_operational_message
from finance.models import PaymentStatus


class CommunicationsServicesTests(SimpleTestCase):
    def test_build_message_body_falls_back_when_student_name_is_blank(self):
        student = SimpleNamespace(full_name="   ")
        enrollment = SimpleNamespace(plan=SimpleNamespace(name="Plano Ouro"))

        message = build_message_body(
            action_kind="reactivation",
            student=student,
            enrollment=enrollment,
        )

        self.assertIn("Oi, aluno.", message)
        self.assertIn("Plano Ouro", message)

    @patch("communications.services.WhatsAppMessageLog.objects.get")
    @patch("communications.services.run_register_operational_message")
    def test_register_operational_message_forwards_minimal_ids_to_facade(
        self,
        run_register_operational_message_mock,
        message_log_get_mock,
    ):
        actor = SimpleNamespace(id=7)
        student = SimpleNamespace(id=11)
        payment = SimpleNamespace(id=13)
        enrollment = SimpleNamespace(id=17)
        message_log = object()

        run_register_operational_message_mock.return_value = SimpleNamespace(message_log_id=23)
        message_log_get_mock.return_value = message_log

        result = register_operational_message(
            actor=actor,
            action_kind="overdue",
            student=student,
            payment=payment,
            enrollment=enrollment,
        )

        self.assertIs(result, message_log)
        run_register_operational_message_mock.assert_called_once_with(
            actor_id=7,
            action_kind="overdue",
            student_id=11,
            payment_id=13,
            enrollment_id=17,
        )
        message_log_get_mock.assert_called_once_with(pk=23)

    def test_normalize_payment_status_accepts_explicit_reference_date(self):
        payment = SimpleNamespace(
            status=PaymentStatus.PENDING,
            due_date="2026-04-10",
        )

        result = normalize_payment_status(payment, reference_date="2026-04-11")

        self.assertIs(result, payment)
        self.assertEqual(payment.status, PaymentStatus.OVERDUE)
