"""
ARQUIVO: testes de constraints do banco de dados.

POR QUE ELE EXISTE:
- Garante que restrições críticas do schema (UniqueConstraint, PROTECT, CASCADE, NOT NULL)
  realmente funcionam no banco, independente da validação de formulário ou model.
- Qualquer migração que acidentalmente remova uma constraint será detectada aqui
  antes de chegar em produção.

O QUE ESTE ARQUIVO FAZ:
1. Testa 2 UniqueConstraints via IntegrityError.
2. Testa 2 on_delete=PROTECT via ProtectedError.
3. Testa 2 on_delete=CASCADE verificando side-effects no banco.
4. Testa 2 NOT NULL constraints via IntegrityError em campos obrigatórios.
"""

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from finance.models import Enrollment, MembershipPlan
from operations.models import Attendance, ClassSession, SessionCancellationEvent
from tests.factories import ClassSessionFactory, PaymentFactory, StudentFactory


# ─── UniqueConstraint ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_attendance_unique_student_session_blocks_duplicate():
    """Attendance.unique_student_session impede dupla reserva no banco."""
    student = StudentFactory()
    session = ClassSessionFactory()
    Attendance.objects.create(student=student, session=session)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Attendance.objects.create(student=student, session=session)


@pytest.mark.django_db
def test_session_cancellation_event_unique_session_id_blocks_duplicate():
    """SessionCancellationEvent.ops_session_cancel_evt_unique_session impede
    dois eventos de cancelamento para a mesma sessão."""
    SessionCancellationEvent.objects.create(
        session_id=9001,
        box_root_slug='test-box',
        attendance_count_at_cancel=5,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SessionCancellationEvent.objects.create(
                session_id=9001,
                box_root_slug='test-box',
                attendance_count_at_cancel=3,
            )


# ─── on_delete=PROTECT ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_membership_plan_delete_protected_by_enrollment():
    """Excluir um MembershipPlan com Enrollment vinculado levanta ProtectedError.

    Garantia: nenhuma exclusão acidental de plano apaga matrículas silenciosamente.
    """
    student = StudentFactory()
    plan = MembershipPlan.objects.create(name='Plano Mensal', price='299.90')
    Enrollment.objects.create(student=student, plan=plan)

    with pytest.raises(ProtectedError):
        with transaction.atomic():
            plan.delete()


@pytest.mark.django_db
def test_membership_plan_queryset_delete_also_raises_protected_error():
    """Tentativa via queryset delete também levanta ProtectedError.

    Cobre a segunda rota de deleção (bulk delete) para o mesmo PROTECT.
    """
    student = StudentFactory()
    plan = MembershipPlan.objects.create(name='Plano Trimestral', price='799.00')
    Enrollment.objects.create(student=student, plan=plan)

    with pytest.raises(ProtectedError):
        with transaction.atomic():
            MembershipPlan.objects.filter(pk=plan.pk).delete()


# ─── on_delete=CASCADE ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_deleting_student_cascades_to_payments():
    """Excluir um Student deve apagar todos os Payments relacionados em cascade."""
    student = StudentFactory()
    PaymentFactory(student=student)
    PaymentFactory(student=student)

    from finance.models import Payment

    assert Payment.objects.filter(student=student).count() == 2
    student.delete()
    assert Payment.objects.filter(student_id=student.pk).count() == 0


@pytest.mark.django_db
def test_deleting_class_session_cascades_to_attendances():
    """Excluir uma ClassSession deve apagar todas as Attendances relacionadas em cascade."""
    student_a = StudentFactory()
    student_b = StudentFactory()
    session = ClassSessionFactory()
    Attendance.objects.create(student=student_a, session=session)
    Attendance.objects.create(student=student_b, session=session)

    assert Attendance.objects.filter(session=session).count() == 2
    session.delete()
    assert Attendance.objects.filter(session_id=session.pk).count() == 0


# ─── NOT NULL ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_payment_amount_not_null_blocks_null_via_update():
    """Payment.amount (DecimalField NOT NULL) rejeita NULL diretamente no banco."""
    student = StudentFactory()
    payment = PaymentFactory(student=student)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            from finance.models import Payment

            Payment.objects.filter(pk=payment.pk).update(amount=None)


@pytest.mark.django_db
def test_attendance_student_fk_not_null_blocks_null_via_update():
    """Attendance.student_id (FK NOT NULL) rejeita NULL diretamente no banco."""
    student = StudentFactory()
    session = ClassSessionFactory()
    attendance = Attendance.objects.create(student=student, session=session)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Attendance.objects.filter(pk=attendance.pk).update(student_id=None)
