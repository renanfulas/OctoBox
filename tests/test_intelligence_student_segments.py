"""
ARQUIVO: testes do segmento do aluno (Onda 7).

POR QUE ELE EXISTE:
- resolve_student_segment() e regra transparente versionada, nao clustering
  opaco — sem teste direto, uma mudanca de limiar (ex: RECURRING_LATE_THRESHOLD)
  muda silenciosamente o rotulo que o dono ve, sem ninguem perceber.
"""

from datetime import date

from django.test import SimpleTestCase, TestCase

from finance.model_definitions import BillingCycle, Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from intelligence.students.segments import (
    NO_AGE_LABEL,
    NO_PLAN_LABEL,
    RULE_VERSION,
    resolve_student_segment,
)
from students.models import Student


class ResolveStudentSegmentPureLogicTests(SimpleTestCase):
    """Casos que nao exigem linha real no banco: Payment.objects.none() e
    modelos nao salvos resolvem sem tocar o Postgres (Django curto-circuita
    EmptyQuerySet e nao consulta atributo de FK ja atribuido em memoria)."""

    def test_age_band_groups_by_decade(self):
        student = Student(full_name='Aluno Idade', phone='5511900000001', birth_date=date(1990, 5, 20))

        segment = resolve_student_segment(
            student=student,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        # 1990-05-20 -> 36 anos em 2026-07-01 (ja fez aniversario no ano)
        self.assertEqual(segment.age_band, '30-39')

    def test_age_band_respects_birthday_not_yet_reached_this_year(self):
        """1996-12-20: em 2026-07-01 o aniversario ainda nao chegou, entao
        a idade e 29 (banda 20-29), nao 30 (banda 30-39) — prova que a
        conta usa (mes, dia) e nao so o ano de nascimento."""
        student = Student(full_name='Aluno Aniversario', phone='5511900000002', birth_date=date(1996, 12, 20))

        segment = resolve_student_segment(
            student=student,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.age_band, '20-29')

    def test_missing_birth_date_falls_back_to_label(self):
        student = Student(full_name='Aluno Sem Idade', phone='5511900000003', birth_date=None)

        segment = resolve_student_segment(
            student=student,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.age_band, NO_AGE_LABEL)

    def test_no_payments_resolves_as_sem_historico(self):
        student = Student(full_name='Aluno Sem Pagamento', phone='5511900000004', birth_date=None)

        segment = resolve_student_segment(
            student=student,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.payment_behavior, 'sem_historico')

    def test_no_enrollment_resolves_billing_cycle_as_sem_plano(self):
        student = Student(full_name='Aluno Sem Plano', phone='5511900000005', birth_date=None)

        segment = resolve_student_segment(
            student=student,
            latest_enrollment=None,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.billing_cycle, NO_PLAN_LABEL)

    def test_billing_cycle_reads_from_unsaved_enrollment_plan(self):
        student = Student(full_name='Aluno Plano', phone='5511900000006', birth_date=None)
        plan = MembershipPlan(name='Trimestral', price='299.90', billing_cycle=BillingCycle.QUARTERLY)
        enrollment = Enrollment(plan=plan, status=EnrollmentStatus.ACTIVE)

        segment = resolve_student_segment(
            student=student,
            latest_enrollment=enrollment,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.billing_cycle, BillingCycle.QUARTERLY)

    def test_segment_key_joins_dimensions_with_pipe(self):
        student = Student(full_name='Aluno Completo', phone='5511900000007', birth_date=date(1995, 1, 1))
        plan = MembershipPlan(name='Trimestral', price='299.90', billing_cycle=BillingCycle.QUARTERLY)
        enrollment = Enrollment(plan=plan, status=EnrollmentStatus.ACTIVE)

        segment = resolve_student_segment(
            student=student,
            latest_enrollment=enrollment,
            payments_queryset=Payment.objects.none(),
            today=date(2026, 7, 1),
        )

        self.assertEqual(segment.segment_key, 'quarterly|sem_historico|30-39')
        self.assertEqual(segment.rule_version, RULE_VERSION)

    def test_channel_is_not_part_of_segment_key(self):
        """O canal resolvido fica FORA do segment_key de proposito — ja
        existe como campo proprio em Student.resolved_acquisition_source
        e nao deve inflar a cardinalidade do segmento."""
        student = Student(
            full_name='Aluno Canal',
            phone='5511900000008',
            birth_date=None,
            resolved_acquisition_source='instagram',
        )

        segment = resolve_student_segment(student=student, payments_queryset=Payment.objects.none(), today=date(2026, 7, 1))

        self.assertNotIn('instagram', segment.segment_key)


class ResolveStudentSegmentPaymentBehaviorIntegrationTests(TestCase):
    """Precisam de linha real no banco (contagem de atraso via
    finance/overdue_metrics.py). Rodar quando Postgres estiver disponivel."""

    def setUp(self):
        self.student = Student.objects.create(full_name='Aluno Pagamento', phone='5511900001000')
        self.plan = MembershipPlan.objects.create(name='Mensal', price='199.90', billing_cycle=BillingCycle.MONTHLY)

    def test_single_late_payment_is_atraso_pontual(self):
        Payment.objects.create(
            student=self.student,
            due_date=date(2026, 6, 1),
            amount='199.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
        )

        segment = resolve_student_segment(student=self.student, today=date(2026, 7, 1))

        self.assertEqual(segment.payment_behavior, 'atraso_pontual')

    def test_two_or_more_late_payments_is_atrasado_recorrente(self):
        Payment.objects.create(
            student=self.student, due_date=date(2026, 5, 1), amount='199.90',
            status=PaymentStatus.PENDING, method=PaymentMethod.PIX,
        )
        Payment.objects.create(
            student=self.student, due_date=date(2026, 6, 1), amount='199.90',
            status=PaymentStatus.PENDING, method=PaymentMethod.PIX,
        )

        segment = resolve_student_segment(student=self.student, today=date(2026, 7, 1))

        self.assertEqual(segment.payment_behavior, 'atrasado_recorrente')

    def test_all_payments_on_time_is_pontual(self):
        Payment.objects.create(
            student=self.student, due_date=date(2026, 6, 1), amount='199.90',
            status=PaymentStatus.PAID, method=PaymentMethod.PIX,
        )

        segment = resolve_student_segment(student=self.student, today=date(2026, 7, 1))

        self.assertEqual(segment.payment_behavior, 'pontual')

    def test_defaults_to_student_payments_manager_when_queryset_not_provided(self):
        Payment.objects.create(
            student=self.student, due_date=date(2026, 6, 1), amount='199.90',
            status=PaymentStatus.PAID, method=PaymentMethod.PIX,
        )
        other_student = Student.objects.create(full_name='Outro Aluno', phone='5511900002000')
        Payment.objects.create(
            student=other_student, due_date=date(2026, 5, 1), amount='99.90',
            status=PaymentStatus.PENDING, method=PaymentMethod.PIX,
        )

        segment = resolve_student_segment(student=self.student, today=date(2026, 7, 1))

        # so os pagamentos do PROPRIO aluno contam — nao vaza entre alunos.
        self.assertEqual(segment.payment_behavior, 'pontual')
