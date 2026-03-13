"""
ARQUIVO: testes unitarios das actions operacionais.

POR QUE ELE EXISTE:
- Protege a camada de mutacao real usada por manager e coach sem depender apenas de testes HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Testa vinculo de pagamento com matricula ativa.
2. Testa criacao de ocorrencia tecnica.
3. Testa acoes de presenca e auditoria.

PONTOS CRITICOS:
- Se estes testes quebrarem, a operacao pode alterar estado errado mesmo com rotas respondendo corretamente.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from auditing.models import AuditEvent
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentStatus
from operations.actions import handle_attendance_action, handle_payment_enrollment_link_action, handle_technical_behavior_note_action
from operations.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession
from students.models import Student


class OperationActionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user('manager-service', password='senha-forte-123')
        self.coach = user_model.objects.create_user('coach-service', password='senha-forte-123')
        self.student = Student.objects.create(full_name='Aluno Teste', phone='5511933333333')
        self.plan = MembershipPlan.objects.create(name='Plano Mensal', price='299.90')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        self.payment = Payment.objects.create(
            student=self.student,
            due_date=timezone.localdate(),
            amount='299.90',
            status=PaymentStatus.PENDING,
        )
        self.session = ClassSession.objects.create(title='WOD 07h', scheduled_at=timezone.now())
        self.attendance = Attendance.objects.create(student=self.student, session=self.session)

    def test_link_payment_to_active_enrollment(self):
        result = handle_payment_enrollment_link_action(actor=self.manager, payment=self.payment)

        self.payment.refresh_from_db()
        self.assertEqual(result.enrollment, self.enrollment)
        self.assertEqual(self.payment.enrollment, self.enrollment)
        self.assertTrue(AuditEvent.objects.filter(action='payment_linked_to_active_enrollment', actor=self.manager).exists())

    def test_create_technical_behavior_note(self):
        note = handle_technical_behavior_note_action(
            actor=self.coach,
            student=self.student,
            category='support',
            description='Aluno relatou desconforto no ombro direito durante o aquecimento.',
        )

        self.assertIsNotNone(note)
        self.assertTrue(BehaviorNote.objects.filter(student=self.student, author=self.coach).exists())
        self.assertTrue(AuditEvent.objects.filter(action='technical_behavior_note_created', actor=self.coach).exists())

    def test_apply_attendance_action(self):
        result = handle_attendance_action(actor=self.coach, attendance=self.attendance, action='check-in')

        self.attendance.refresh_from_db()
        self.assertEqual(result.status, AttendanceStatus.CHECKED_IN)
        self.assertEqual(self.attendance.status, AttendanceStatus.CHECKED_IN)
        self.assertTrue(AuditEvent.objects.filter(action='attendance_check-in', actor=self.coach).exists())

    def test_apply_invalid_attendance_action_returns_none(self):
        result = handle_attendance_action(actor=self.coach, attendance=self.attendance, action='invalid')

        self.assertIsNone(result)
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.status, AttendanceStatus.BOOKED)