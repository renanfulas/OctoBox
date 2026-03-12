"""
ARQUIVO: testes unitarios de handlers e workflows do catalogo.

POR QUE ELE EXISTE:
- Protege a camada de regra aplicada diretamente pelos services, sem depender apenas de testes HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Testa workflows de aluno e plano.
2. Testa handlers de pagamento, matricula e comunicacao operacional.
3. Verifica efeitos em banco e auditoria nas fronteiras de negocio do catalogo.

PONTOS CRITICOS:
- Se estes testes quebrarem, a regra de negocio pode falhar mesmo quando a view ainda responde 200 ou 302.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from boxcore.catalog.services import (
    build_operational_queue_metrics,
    build_operational_queue_snapshot,
    handle_finance_communication_action,
    handle_student_enrollment_action,
    handle_student_payment_action,
    run_membership_plan_create_workflow,
    run_membership_plan_update_workflow,
    run_student_quick_create_workflow,
    run_student_quick_update_workflow,
    sync_student_intake,
)
from boxcore.catalog.services.payments import create_payment_schedule, regenerate_payment
from boxcore.models import (
    AuditEvent,
    Enrollment,
    EnrollmentStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Student,
    StudentIntake,
    WhatsAppMessageLog,
)


class DummySavedForm:
    def __init__(self, *, save_callback, cleaned_data, changed_data=None, instance=None):
        self._save_callback = save_callback
        self.cleaned_data = cleaned_data
        self.changed_data = changed_data or []
        self.instance = instance

    def save(self):
        return self._save_callback()


class CatalogServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='service-owner',
            email='service-owner@example.com',
            password='senha-forte-123',
        )
        self.plan = MembershipPlan.objects.create(name='Cross Prime', price=Decimal('289.90'), billing_cycle='monthly')
        self.plan_plus = MembershipPlan.objects.create(name='Cross Black', price=Decimal('349.90'), billing_cycle='monthly')
        self.student = Student.objects.create(full_name='Bruna Costa', phone='5511988888888', status='active')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan, status=EnrollmentStatus.ACTIVE)
        self.payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            amount='289.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        self.intake = StudentIntake.objects.create(full_name='Lead Bruna', phone='5511970000000', email='lead@example.com')

    def test_student_create_workflow_creates_sales_flow_and_audits(self):
        def save_student():
            return Student.objects.create(full_name='Mateus Oliveira', phone='5511977777777', status='active')

        form = DummySavedForm(
            save_callback=save_student,
            cleaned_data={
                'full_name': 'Mateus Oliveira',
                'phone': '5511977777777',
                'status': 'active',
                'email': '',
                'gender': '',
                'birth_date': None,
                'health_issue_status': '',
                'cpf': '',
                'notes': '',
                'selected_plan': self.plan,
                'enrollment_status': EnrollmentStatus.ACTIVE,
                'payment_due_date': timezone.localdate(),
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': True,
                'payment_reference': '',
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 1,
                'initial_payment_amount': None,
                'intake_record': self.intake,
            },
        )

        result = run_student_quick_create_workflow(actor=self.user, form=form, selected_intake=self.intake)

        self.assertEqual(result['student'].full_name, 'Mateus Oliveira')
        self.assertTrue(result['student'].enrollments.filter(plan=self.plan, status=EnrollmentStatus.ACTIVE).exists())
        self.assertTrue(result['student'].payments.filter(status=PaymentStatus.PAID).exists())
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.linked_student, result['student'])
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_created').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_payment_created').exists())

    def test_student_update_workflow_updates_plan_and_audits(self):
        def update_student():
            self.student.full_name = 'Bruna Costa Lima'
            self.student.save(update_fields=['full_name', 'updated_at'])
            return self.student

        form = DummySavedForm(
            save_callback=update_student,
            cleaned_data={
                'full_name': 'Bruna Costa Lima',
                'phone': self.student.phone,
                'status': self.student.status,
                'email': self.student.email,
                'gender': self.student.gender,
                'birth_date': self.student.birth_date,
                'health_issue_status': self.student.health_issue_status,
                'cpf': self.student.cpf,
                'notes': self.student.notes,
                'selected_plan': self.plan_plus,
                'enrollment_status': EnrollmentStatus.ACTIVE,
                'payment_due_date': timezone.localdate(),
                'payment_method': PaymentMethod.CREDIT_CARD,
                'confirm_payment_now': False,
                'payment_reference': '',
                'billing_strategy': 'installments',
                'installment_total': 3,
                'recurrence_cycles': 1,
                'initial_payment_amount': None,
                'intake_record': None,
            },
            changed_data=['full_name', 'selected_plan'],
            instance=self.student,
        )

        result = run_student_quick_update_workflow(actor=self.user, form=form, changed_fields=form.changed_data)

        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, 'Bruna Costa Lima')
        self.assertTrue(self.student.enrollments.filter(plan=self.plan_plus, status=EnrollmentStatus.ACTIVE).exists())
        self.assertEqual(self.student.payments.filter(enrollment__plan=self.plan_plus).count(), 3)
        self.assertEqual(result['enrollment_sync']['movement'], 'upgrade')
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_updated').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_plan_changed').exists())

    def test_payment_handler_marks_payment_paid(self):
        handle_student_payment_action(
            actor=self.user,
            student=self.student,
            payment=self.payment,
            action='mark-paid',
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PAID)
        self.assertTrue(AuditEvent.objects.filter(action='student_payment_marked_paid').exists())

    def test_enrollment_handler_cancels_and_reactivates(self):
        handle_student_enrollment_action(
            actor=self.user,
            student=self.student,
            enrollment=self.enrollment,
            action='cancel-enrollment',
            action_date=timezone.localdate(),
            reason='Mudanca de rotina.',
        )

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.CANCELED)

        handle_student_enrollment_action(
            actor=self.user,
            student=self.student,
            enrollment=self.enrollment,
            action='reactivate-enrollment',
            action_date=timezone.localdate(),
            reason='Retorno ao box.',
        )

        self.assertEqual(self.student.enrollments.filter(status=EnrollmentStatus.ACTIVE).count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action='student_enrollment_reactivated').exists())

    def test_plan_workflows_create_and_update(self):
        create_form = DummySavedForm(
            save_callback=lambda: MembershipPlan.objects.create(name='Legends Unlimited', price=Decimal('429.90'), billing_cycle='monthly'),
            cleaned_data={},
        )
        created_plan = run_membership_plan_create_workflow(actor=self.user, form=create_form)
        self.assertEqual(created_plan.name, 'Legends Unlimited')
        self.assertTrue(AuditEvent.objects.filter(action='membership_plan_quick_created').exists())

        def update_plan():
            self.plan.name = 'Cross Gold Plus'
            self.plan.price = Decimal('339.90')
            self.plan.save(update_fields=['name', 'price', 'updated_at'])
            return self.plan

        update_form = DummySavedForm(
            save_callback=update_plan,
            cleaned_data={},
            changed_data=['name', 'price'],
        )
        updated_plan = run_membership_plan_update_workflow(actor=self.user, form=update_form, changed_fields=update_form.changed_data)
        self.assertEqual(updated_plan.name, 'Cross Gold Plus')
        self.assertTrue(AuditEvent.objects.filter(action='membership_plan_quick_updated').exists())

    def test_finance_communication_handler_registers_message(self):
        overdue_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=3),
            amount='289.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        result = handle_finance_communication_action(
            actor=self.user,
            payload={
                'action_kind': 'overdue',
                'student_id': self.student.id,
                'payment_id': overdue_payment.id,
            },
        )

        overdue_payment.refresh_from_db()
        self.assertEqual(result['student'], self.student)
        self.assertEqual(overdue_payment.status, PaymentStatus.OVERDUE)
        self.assertTrue(WhatsAppMessageLog.objects.filter(contact__linked_student=self.student).exists())
        self.assertTrue(AuditEvent.objects.filter(action='operational_whatsapp_touch_registered').exists())

    def test_create_payment_schedule_creates_installments(self):
        first_payment = create_payment_schedule(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate(),
            payment_method=PaymentMethod.PIX,
            confirm_payment_now=True,
            note='Parcelamento de teste.',
            amount=Decimal('300.00'),
            reference='ref-installment',
            billing_strategy='installments',
            installment_total=3,
            recurrence_cycles=1,
        )

        created_payments = list(Payment.objects.filter(reference='ref-installment').order_by('installment_number'))
        self.assertEqual(first_payment.id, created_payments[0].id)
        self.assertEqual(len(created_payments), 3)
        self.assertEqual([item.amount for item in created_payments], [Decimal('100.00'), Decimal('100.00'), Decimal('100.00')])
        self.assertEqual(created_payments[0].status, PaymentStatus.PAID)
        self.assertEqual(created_payments[1].status, PaymentStatus.PENDING)

    def test_regenerate_payment_creates_next_payment(self):
        regenerated_payment = regenerate_payment(student=self.student, payment=self.payment, enrollment=self.enrollment)

        self.assertIsNotNone(regenerated_payment)
        self.assertEqual(regenerated_payment.installment_number, self.payment.installment_number + 1)
        self.assertEqual(regenerated_payment.amount, Decimal(self.payment.amount))
        self.assertEqual(regenerated_payment.status, PaymentStatus.PENDING)
        self.assertEqual(regenerated_payment.billing_group, self.payment.billing_group or regenerated_payment.billing_group)

    def test_operational_queue_snapshot_builds_prioritized_items_and_metrics(self):
        self.payment.status = PaymentStatus.PAID
        self.payment.save(update_fields=['status', 'updated_at'])

        overdue_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=2),
            amount='289.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        upcoming_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() + timezone.timedelta(days=2),
            amount='289.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )
        canceled_enrollment = Enrollment.objects.create(
            student=self.student,
            plan=self.plan,
            status=EnrollmentStatus.CANCELED,
            start_date=timezone.localdate() - timezone.timedelta(days=40),
            end_date=timezone.localdate() - timezone.timedelta(days=5),
        )

        queue = build_operational_queue_snapshot(limit=9)
        metrics = build_operational_queue_metrics(queue)

        self.assertTrue(any(item['kind'] == 'upcoming' and item['payment'].id == upcoming_payment.id for item in queue))
        self.assertTrue(any(item['kind'] == 'overdue' and item['payment'].id == overdue_payment.id for item in queue))
        self.assertTrue(any(item['kind'] == 'reactivation' and item['enrollment'].id == canceled_enrollment.id for item in queue))
        self.assertEqual(metrics['Vencendo nos proximos dias'], 1)
        self.assertEqual(metrics['Cobrancas em atraso'], 1)
        self.assertEqual(metrics['Chance de reativacao'], 1)

    def test_sync_student_intake_links_latest_matching_lead_by_phone(self):
        self.intake.delete()
        older_intake = StudentIntake.objects.create(
            full_name='Lead Antigo',
            phone='(11) 97000-0000',
            email='old@example.com',
        )
        latest_intake = StudentIntake.objects.create(
            full_name='Lead Recente',
            phone='5511970000000',
            email='new@example.com',
        )
        self.student.phone = '(11) 97000-0000'
        self.student.save(update_fields=['phone', 'updated_at'])

        linked_intake = sync_student_intake(student=self.student)

        self.assertEqual(linked_intake.id, latest_intake.id)
        latest_intake.refresh_from_db()
        older_intake.refresh_from_db()
        self.assertEqual(latest_intake.linked_student_id, self.student.id)
        self.assertEqual(latest_intake.status, 'approved')
        self.assertIsNone(older_intake.linked_student_id)