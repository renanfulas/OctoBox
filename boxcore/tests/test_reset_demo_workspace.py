"""
ARQUIVO: testes do reset da base ficticia de demo.

POR QUE ELE EXISTE:
- Garante que o reset destrutivo recrie um cenario consistente de box funcionando sem herdar lixo da base anterior.

O QUE ESTE ARQUIVO FAZ:
1. Prepara dados antigos de alunos e fluxo comercial.
2. Executa o comando de reset da demo.
3. Confirma que os dados antigos sairam e a nova massa ficticia foi criada.

PONTOS CRITICOS:
- Se esse teste falhar, o comando pode estar deixando residuos antigos ou montando uma demo incompleta.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from communications.models import StudentIntake, WhatsAppContact, WhatsAppMessageLog
from finance.models import Enrollment, MembershipPlan, Payment
from onboarding.models import IntakeSource
from operations.models import Attendance, BehaviorNote, ClassSession, SessionStatus
from students.models import Student, StudentStatus


class ResetDemoWorkspaceCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='qa_owner_browser',
            email='qa_owner_browser@example.com',
            password='senha-forte-123',
        )
        user_model.objects.create_user(
            username='qa_coach',
            email='qa_coach@example.com',
            password='senha-forte-123',
        )
        user_model.objects.create_user(
            username='copilot-demo-coach',
            email='copilot-demo-coach@example.com',
            password='senha-forte-123',
        )

        old_student = Student.objects.create(
            full_name='Aluno Real Antigo',
            phone='5511999990001',
            status=StudentStatus.ACTIVE,
        )
        old_plan = MembershipPlan.objects.create(name='Plano Antigo', price='199.90')
        old_enrollment = Enrollment.objects.create(student=old_student, plan=old_plan)
        old_session = ClassSession.objects.create(
            title='Aula Antiga',
            coach=self.owner,
            scheduled_at='2026-03-10T07:00:00Z',
            status=SessionStatus.SCHEDULED,
        )
        Payment.objects.create(
            student=old_student,
            enrollment=old_enrollment,
            due_date='2026-03-11',
            amount='199.90',
            reference='ANTIGO-001',
        )
        Attendance.objects.create(student=old_student, session=old_session)
        BehaviorNote.objects.create(student=old_student, author=self.owner, description='Observacao antiga.')
        StudentIntake.objects.create(
            full_name='Lead Antigo',
            phone='5511999990002',
            source=IntakeSource.MANUAL,
        )
        old_contact = WhatsAppContact.objects.create(phone='5511999990003', linked_student=old_student)
        WhatsAppMessageLog.objects.create(contact=old_contact, body='Mensagem antiga')

    def test_reset_demo_workspace_replaces_existing_business_data(self):
        call_command('reset_demo_workspace')

        self.assertFalse(Student.objects.filter(full_name='Aluno Real Antigo').exists())
        self.assertEqual(Student.objects.count(), 14)
        self.assertTrue(Student.objects.filter(full_name='Alice Braga', status=StudentStatus.ACTIVE).exists())
        self.assertTrue(Student.objects.filter(full_name='Kaique Lima', status=StudentStatus.LEAD).exists())

        self.assertEqual(MembershipPlan.objects.filter(name__startswith='Piloto ').count(), 3)
        self.assertEqual(Enrollment.objects.count(), 10)
        self.assertEqual(Payment.objects.filter(reference__startswith='PILOTO-').count(), 16)
        self.assertEqual(ClassSession.objects.count(), 12)
        self.assertEqual(Attendance.objects.count(), 51)
        self.assertEqual(BehaviorNote.objects.count(), 3)
        self.assertEqual(StudentIntake.objects.count(), 4)
        self.assertEqual(WhatsAppContact.objects.count(), 4)
        self.assertEqual(WhatsAppMessageLog.objects.count(), 6)

    def test_reset_demo_workspace_supports_reception_conversion_scenario(self):
        call_command('reset_demo_workspace', scenario='reception-conversion')

        self.assertEqual(Student.objects.count(), 14)
        self.assertEqual(MembershipPlan.objects.filter(name__startswith='Piloto ').count(), 3)
        self.assertEqual(Enrollment.objects.count(), 10)
        self.assertEqual(Payment.objects.filter(reference__startswith='PILOTO-').count(), 16)
        self.assertEqual(ClassSession.objects.count(), 12)
        self.assertEqual(Attendance.objects.count(), 51)
        self.assertEqual(BehaviorNote.objects.count(), 3)
        self.assertEqual(StudentIntake.objects.count(), 7)
        self.assertEqual(WhatsAppContact.objects.count(), 7)
        self.assertEqual(WhatsAppMessageLog.objects.count(), 12)
        self.assertTrue(StudentIntake.objects.filter(full_name='Sofia Mello').exists())
        self.assertTrue(WhatsAppContact.objects.filter(display_name='Valentina Cruz').exists())