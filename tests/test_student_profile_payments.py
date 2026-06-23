"""
ARQUIVO: testes da apresentacao de cobrancas do aluno no Perfil (self-service).

POR QUE EXISTE:
- Garante que o aluno ve as PROPRIAS cobrancas, com status correto (PENDING
  vencida vira 'overdue' na apresentacao) e a contagem de cobrancas em aberto.
"""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from finance.models import PaymentStatus
from student_app.student_payments_presentation import (
    build_student_payment_rows,
    count_open_payments,
)
from tests.factories import PaymentFactory, StudentFactory

TODAY = date(2026, 6, 22)


class StudentProfilePaymentsPresentationTests(TestCase):
    def test_rows_reflect_status_and_count_open(self):
        student = StudentFactory()
        PaymentFactory(student=student, status=PaymentStatus.PENDING, due_date=date(2026, 5, 1), amount='100.00')  # vencida -> overdue
        PaymentFactory(student=student, status=PaymentStatus.PENDING, due_date=date(2026, 7, 1), amount='120.00')  # futura -> pending
        PaymentFactory(student=student, status=PaymentStatus.PAID, due_date=date(2026, 4, 1), amount='90.00')

        rows = build_student_payment_rows(student, today=TODAY)

        self.assertEqual(len(rows), 3)
        self.assertEqual(sorted(r['status'] for r in rows), ['overdue', 'paid', 'pending'])
        # Em aberto = pendente + atrasada.
        self.assertEqual(count_open_payments(rows), 2)

    def test_overdue_pending_is_labeled_atrasado(self):
        student = StudentFactory()
        PaymentFactory(student=student, status=PaymentStatus.PENDING, due_date=date(2026, 1, 1), amount='50.00')

        rows = build_student_payment_rows(student, today=TODAY)

        self.assertEqual(rows[0]['status'], 'overdue')
        self.assertEqual(rows[0]['status_label'], 'Atrasado')

    def test_paid_payment_keeps_status_and_is_not_open(self):
        student = StudentFactory()
        PaymentFactory(student=student, status=PaymentStatus.PAID, due_date=date(2026, 6, 1), amount='80.00')

        rows = build_student_payment_rows(student, today=TODAY)

        self.assertEqual(rows[0]['status'], 'paid')
        self.assertEqual(count_open_payments(rows), 0)

    def test_only_own_student_payments(self):
        owner = StudentFactory()
        other = StudentFactory()
        PaymentFactory(student=other, status=PaymentStatus.PENDING, due_date=date(2026, 5, 1), amount='100.00')

        rows = build_student_payment_rows(owner, today=TODAY)

        self.assertEqual(rows, [])
