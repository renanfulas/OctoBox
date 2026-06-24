"""
ARQUIVO: testes do fluxo de pagamento iniciado pelo aluno (P3).

POR QUE EXISTE:
- Protege a logica de seguranca (a fatura precisa ser do PROPRIO aluno e estar em
  aberto) e a adaptacao do create_checkout_session para o app do aluno (URLs de
  retorno proprias + ator anonimo).
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase, TestCase

from finance.models import PaymentStatus
from integrations.stripe.services import create_checkout_session
from student_app.student_payments_presentation import (
    build_student_payment_rows,
    resolve_payable_student_invoice,
)
from tests.factories import PaymentFactory, StudentFactory


class ResolvePayableInvoiceTests(TestCase):
    def test_returns_open_invoice_of_own_student(self):
        student = StudentFactory()
        payment = PaymentFactory(student=student, status=PaymentStatus.PENDING, amount='100.00')

        self.assertEqual(resolve_payable_student_invoice(student, payment.id), payment)

    def test_none_for_other_students_invoice(self):
        owner = StudentFactory()
        other = StudentFactory()
        payment = PaymentFactory(student=other, status=PaymentStatus.PENDING, amount='100.00')

        self.assertIsNone(resolve_payable_student_invoice(owner, payment.id))

    def test_none_for_paid_invoice(self):
        student = StudentFactory()
        payment = PaymentFactory(student=student, status=PaymentStatus.PAID, amount='100.00')

        self.assertIsNone(resolve_payable_student_invoice(student, payment.id))

    def test_none_for_nonexistent_invoice(self):
        student = StudentFactory()
        self.assertIsNone(resolve_payable_student_invoice(student, 999_999))

    def test_rows_carry_id_and_is_open(self):
        student = StudentFactory()
        PaymentFactory(student=student, status=PaymentStatus.PENDING, due_date=date(2026, 5, 1), amount='100.00')

        rows = build_student_payment_rows(student, today=date(2026, 6, 22))

        self.assertIn('id', rows[0])
        self.assertTrue(rows[0]['is_open'])  # PENDING vencida -> em aberto


class StudentCheckoutAdaptationTests(SimpleTestCase):
    def _request(self):
        request = RequestFactory().post('/aluno/pagamentos/5/pagar/')
        request.user = AnonymousUser()
        return request

    def _payment(self):
        return SimpleNamespace(
            id=5, version=0, status='pending', amount=100.0, notes='',
            student=SimpleNamespace(id=3, full_name='Aluno Teste'),
            enrollment=None, installment_number=1, installment_total=1,
        )

    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.checkout.Session.create')
    def test_custom_return_urls_and_anonymous_actor(self, session_mock, audit_mock):
        session_mock.return_value = SimpleNamespace(id='cs_1', url='https://stripe.test/cs_1')

        url = create_checkout_session(
            self._payment(), self._request(),
            success_url='https://app.test/aluno/pagamentos/sucesso/',
            cancel_url='https://app.test/aluno/pagamentos/cancelado/',
        )

        self.assertEqual(url, 'https://stripe.test/cs_1')
        kwargs = session_mock.call_args.kwargs
        self.assertEqual(kwargs['success_url'], 'https://app.test/aluno/pagamentos/sucesso/')
        self.assertEqual(kwargs['cancel_url'], 'https://app.test/aluno/pagamentos/cancelado/')
        # Aluno anonimo (sem request.user autenticado) -> ator do audit e None.
        self.assertIsNone(audit_mock.call_args.kwargs['actor'])
