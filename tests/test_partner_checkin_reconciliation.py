"""
ARQUIVO: testes do ledger de reconciliacao de check-in de parceiro (Wellhub/TotalPass).

POR QUE EXISTE:
- Garante que: (1) o check-in de um aluno de parceiro cria o ledger pending e
  o de um aluno direto nao cria nada; (2) o lembrete so dispara na janela
  0/10/30min e avanca o estado sem nunca chamar a API do parceiro; (3) so o
  extrato oficial (reconcile_partner_statement) reconhece receita; (4) check-in
  sem confirmacao nem reconciliacao vira disputed apos o prazo, nunca receita
  presumida.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import TestCase
from django.utils import timezone
from django_tenants.utils import schema_context

from finance.models import EnrollmentStatus, PartnerCheckInCharge, PartnerCheckInStatus, PaymentSource
from finance.partner_checkin_reminders import (
    confirm_partner_checkin,
    is_reminder_due,
    next_reminder_offset_minutes,
    send_due_partner_checkin_reminders,
    send_partner_checkin_reminder,
    sync_partner_checkin_charge,
)
from finance.reconciliation import flag_stale_partner_checkins, reconcile_partner_statement
from tests.factories import AttendanceFactory, EnrollmentFactory, StudentFactory

TENANT_SCHEMA = 'box_test'


class ReminderScheduleTests(TestCase):
    """Funcoes puras (sem banco): decisao de quando um lembrete e devido."""

    def test_offsets_are_0_10_30_then_none(self):
        self.assertEqual(next_reminder_offset_minutes(0), 0)
        self.assertEqual(next_reminder_offset_minutes(1), 10)
        self.assertEqual(next_reminder_offset_minutes(2), 30)
        self.assertIsNone(next_reminder_offset_minutes(3))

    def test_is_reminder_due_respects_offset(self):
        scheduled_at = timezone.now()

        self.assertTrue(is_reminder_due(session_scheduled_at=scheduled_at, attempts_sent=0, now=scheduled_at))
        self.assertFalse(is_reminder_due(
            session_scheduled_at=scheduled_at, attempts_sent=1, now=scheduled_at + timedelta(minutes=5),
        ))
        self.assertTrue(is_reminder_due(
            session_scheduled_at=scheduled_at, attempts_sent=1, now=scheduled_at + timedelta(minutes=10),
        ))
        self.assertFalse(is_reminder_due(session_scheduled_at=scheduled_at, attempts_sent=3, now=scheduled_at + timedelta(days=1)))


@pytest.mark.public_schema
class PartnerCheckInChargeSyncTests(TestCase):
    def test_checkin_creates_pending_charge_for_partner_enrollment(self):
        with schema_context(TENANT_SCHEMA):
            enrollment = EnrollmentFactory(payment_source=PaymentSource.WELLHUB, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=enrollment.student, check_in_at=timezone.now())

            charge = PartnerCheckInCharge.objects.get(attendance=attendance)
            self.assertEqual(charge.status, PartnerCheckInStatus.PENDING)
            self.assertEqual(charge.partner, PaymentSource.WELLHUB)
            self.assertEqual(charge.enrollment_id, enrollment.id)

    def test_checkin_direct_student_creates_no_charge(self):
        with schema_context(TENANT_SCHEMA):
            enrollment = EnrollmentFactory(payment_source=PaymentSource.DIRECT, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=enrollment.student, check_in_at=timezone.now())

            self.assertFalse(PartnerCheckInCharge.objects.filter(attendance=attendance).exists())

    def test_booked_without_checkin_creates_no_charge(self):
        with schema_context(TENANT_SCHEMA):
            enrollment = EnrollmentFactory(payment_source=PaymentSource.TOTALPASS, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=enrollment.student)

            self.assertFalse(PartnerCheckInCharge.objects.filter(attendance=attendance).exists())

    def test_sync_is_idempotent_on_resave(self):
        with schema_context(TENANT_SCHEMA):
            enrollment = EnrollmentFactory(payment_source=PaymentSource.WELLHUB, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=enrollment.student, check_in_at=timezone.now())
            attendance.notes = 'atualizado'
            attendance.save()

            self.assertEqual(PartnerCheckInCharge.objects.filter(attendance=attendance).count(), 1)


@pytest.mark.public_schema
class PartnerCheckInReminderSendingTests(TestCase):
    def _pending_charge(self, *, session_scheduled_at, email='aluno@example.com'):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(email=email)
            EnrollmentFactory(student=student, payment_source=PaymentSource.WELLHUB, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=student, check_in_at=timezone.now())
            attendance.session.scheduled_at = session_scheduled_at
            attendance.session.save(update_fields=['scheduled_at'])
            return PartnerCheckInCharge.objects.get(attendance=attendance)

    @patch('signup.email_sender.send_html_email')
    def test_reminder_sent_and_advances_state(self, send_mock):
        with schema_context(TENANT_SCHEMA):
            charge = self._pending_charge(session_scheduled_at=timezone.now())

            result = send_partner_checkin_reminder(charge)

            charge.refresh_from_db()
            self.assertEqual(result, 'sent')
            self.assertEqual(charge.status, PartnerCheckInStatus.REMINDED)
            self.assertEqual(charge.reminder_attempts, 1)
            self.assertIsNotNone(charge.last_reminder_at)
            self.assertEqual(send_mock.call_args.kwargs['to_email'], 'aluno@example.com')

    @patch('signup.email_sender.send_html_email')
    def test_reminder_skipped_without_email(self, send_mock):
        with schema_context(TENANT_SCHEMA):
            charge = self._pending_charge(session_scheduled_at=timezone.now(), email='')

            result = send_partner_checkin_reminder(charge)

            self.assertEqual(result, 'skipped')
            send_mock.assert_not_called()

    @patch('signup.email_sender.send_html_email')
    def test_due_reminders_respect_the_0_10_30_window(self, _send_mock):
        with schema_context(TENANT_SCHEMA):
            now = timezone.now()
            # Aula comecou 5min atras: a janela dos 0min ja esta aberta.
            charge = self._pending_charge(session_scheduled_at=now - timedelta(minutes=5))

            first_report = send_due_partner_checkin_reminders(now=now)
            self.assertEqual(first_report['sent'], 1)
            charge.refresh_from_db()
            self.assertEqual(charge.reminder_attempts, 1)

            # +5min = 10min desde o inicio da aula: janela dos 10min abre agora.
            second_report = send_due_partner_checkin_reminders(now=now + timedelta(minutes=5))
            self.assertEqual(second_report['sent'], 1)
            charge.refresh_from_db()
            self.assertEqual(charge.reminder_attempts, 2)

            # +1min: ainda nao chegou aos 30min desde a aula, nada e enviado.
            third_report = send_due_partner_checkin_reminders(now=now + timedelta(minutes=6))
            self.assertEqual(third_report['sent'], 0)
            charge.refresh_from_db()
            self.assertEqual(charge.reminder_attempts, 2)

    def test_confirm_marks_confirmed(self):
        with schema_context(TENANT_SCHEMA):
            charge = self._pending_charge(session_scheduled_at=timezone.now())

            confirmed = confirm_partner_checkin(charge.id)

            charge.refresh_from_db()
            self.assertTrue(confirmed)
            self.assertEqual(charge.status, PartnerCheckInStatus.CONFIRMED)
            self.assertIsNotNone(charge.confirmed_at)


@pytest.mark.public_schema
class PartnerStatementReconciliationTests(TestCase):
    def _wellhub_charge_on(self, *, phone, session_date):
        with schema_context(TENANT_SCHEMA):
            student = StudentFactory(phone=phone)
            EnrollmentFactory(student=student, payment_source=PaymentSource.WELLHUB, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=student, check_in_at=timezone.now())
            attendance.session.scheduled_at = timezone.make_aware(datetime.combine(session_date, datetime.min.time()))
            attendance.session.save(update_fields=['scheduled_at'])
            return sync_partner_checkin_charge(attendance)

    def test_statement_row_reconciles_matching_charge(self):
        session_date = timezone.localdate()
        charge = self._wellhub_charge_on(phone='5511900999999', session_date=session_date)

        report = reconcile_partner_statement(
            partner=PaymentSource.WELLHUB,
            rows=[{'student_phone': '5511900999999', 'date': session_date.isoformat(), 'value': '12.50'}],
            statement_reference='2026-08',
        )

        self.assertEqual(report['matched'], 1)
        self.assertEqual(report['orphan_count'], 0)
        with schema_context(TENANT_SCHEMA):
            charge.refresh_from_db()
            self.assertEqual(charge.status, PartnerCheckInStatus.RECONCILED)
            self.assertEqual(str(charge.declared_value), '12.50')
            self.assertEqual(charge.statement_reference, '2026-08')

    def test_statement_row_without_match_is_orphan(self):
        report = reconcile_partner_statement(
            partner=PaymentSource.WELLHUB,
            rows=[{'student_phone': '5511900000000', 'date': '2026-01-01', 'value': '10.00'}],
        )

        self.assertEqual(report['matched'], 0)
        self.assertEqual(report['orphan_count'], 1)

    def test_stale_unconfirmed_charge_is_flagged_disputed(self):
        with schema_context(TENANT_SCHEMA):
            enrollment = EnrollmentFactory(payment_source=PaymentSource.TOTALPASS, status=EnrollmentStatus.ACTIVE)
            attendance = AttendanceFactory(student=enrollment.student, check_in_at=timezone.now())
            charge = sync_partner_checkin_charge(attendance)
            PartnerCheckInCharge.objects.filter(id=charge.id).update(created_at=timezone.now() - timedelta(days=10))

        report = flag_stale_partner_checkins(older_than_days=3)

        self.assertEqual(report['flagged_count'], 1)
        with schema_context(TENANT_SCHEMA):
            charge.refresh_from_db()
            self.assertEqual(charge.status, PartnerCheckInStatus.DISPUTED)
