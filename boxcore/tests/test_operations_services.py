"""
ARQUIVO: testes unitarios das actions e services operacionais.

POR QUE ELE EXISTE:
- Protege a camada de mutacao real usada por manager e coach sem depender apenas de testes HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Testa vinculo de pagamento com matricula ativa.
2. Testa criacao de ocorrencia tecnica.
3. Testa acoes de presenca e auditoria.
4. Testa importacao de contatos usada em configuracoes operacionais.

PONTOS CRITICOS:
- Se estes testes quebrarem, a operacao pode alterar estado errado mesmo com rotas respondendo corretamente.
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from auditing.models import AuditEvent
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentStatus
from onboarding.models import StudentIntake
from operations.actions import handle_attendance_action, handle_payment_enrollment_link_action, handle_technical_behavior_note_action
from operations.models import (
    Attendance,
    AttendanceStatus,
    BehaviorNote,
    ClassSession,
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
)
from operations.services.contact_importer import import_contacts_from_list, import_contacts_from_stream
from shared_support.crypto_fields import generate_blind_index
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

    def test_import_contacts_from_stream_creates_intake_from_csv(self):
        stream = BytesIO(b'Nome,Telefone,Email\nMaria Silva,(11) 99888-7766,maria@example.com\n')

        report = import_contacts_from_stream(stream, source_platform='whatsapp', actor=self.manager)

        self.assertEqual(report['success'], 1)
        intake = StudentIntake.objects.get(full_name='Maria Silva')
        self.assertEqual(intake.full_name, 'Maria Silva')
        self.assertEqual(intake.phone, '5511998887766')
        self.assertEqual(intake.phone_lookup_index, generate_blind_index('5511998887766'))
        self.assertEqual(intake.email, 'maria@example.com')
        self.assertEqual(intake.assigned_to, self.manager)

    def test_import_contacts_from_list_reports_database_phone_duplicates(self):
        existing_intake = StudentIntake.objects.create(
            full_name='Lead Existente',
            phone='5511998887766',
            email='existente@example.com',
        )

        report = import_contacts_from_list(
            [{'Nome': 'Maria Silva', 'Telefone': '(11) 99888-7766', 'Email': 'nova@example.com'}],
            source_platform='whatsapp',
            actor=self.manager,
        )

        self.assertEqual(report['success'], 0)
        self.assertEqual(report['duplicates'], 1)
        self.assertEqual(report['errors'], 0)
        self.assertEqual(report['duplicate_details'][0]['reason'], 'duplicate_in_database_phone')
        self.assertEqual(report['duplicate_details'][0]['existing_intake_id'], existing_intake.id)
        self.assertEqual(report['duplicate_details'][0]['normalized_phone'], '5511998887766')

    def test_import_contacts_from_list_reports_file_email_duplicates(self):
        report = import_contacts_from_list(
            [
                {'Nome': 'Lead 1', 'Telefone': '(11) 99888-7766', 'Email': 'duplicado@example.com'},
                {'Nome': 'Lead 2', 'Telefone': '(11) 97777-6655', 'Email': 'DUPLICADO@example.com'},
            ],
            source_platform='whatsapp',
            actor=self.manager,
        )

        self.assertEqual(report['success'], 1)
        self.assertEqual(report['duplicates'], 1)
        self.assertEqual(report['errors'], 0)
        self.assertEqual(report['duplicate_details'][0]['reason'], 'duplicate_in_file_email')
        self.assertEqual(report['duplicate_details'][0]['normalized_email'], 'duplicado@example.com')

    def test_lead_import_job_starts_with_foundation_defaults(self):
        job = LeadImportJob.objects.create(
            created_by=self.manager,
            source_type=LeadImportSourceType.WHATSAPP_LIST,
            declared_range=LeadImportDeclaredRange.UP_TO_200,
        )

        self.assertEqual(job.processing_mode, LeadImportProcessingMode.SYNC)
        self.assertEqual(job.status, LeadImportJobStatus.RECEIVED)
        self.assertEqual(job.detected_lead_count, 0)
        self.assertEqual(job.success_count, 0)
        self.assertEqual(job.duplicate_count, 0)
        self.assertEqual(job.error_count, 0)
        self.assertEqual(job.duplicate_details, [])
        self.assertEqual(job.error_details, [])
