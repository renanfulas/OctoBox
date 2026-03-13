"""
ARQUIVO: adapters Django de auditoria do dominio de alunos.

POR QUE ELE EXISTE:
- Isola a escrita concreta de auditoria para que adapters de quick flow e actions nao dependam diretamente de log_audit_event.

O QUE ESTE ARQUIVO FAZ:
1. Reidrata actor e alvos ORM do quick flow de aluno.
2. Registra eventos de criacao, atualizacao, cobranca e conversao de intake.
3. Registra eventos concretos das actions comerciais de pagamento e matricula.

PONTOS CRITICOS:
- Esta camada pode usar ORM e auditoria concreta livremente, mas nao deve concentrar a persistencia principal dos fluxos.
"""

from django.contrib.auth import get_user_model

from auditing import log_audit_event
from communications.models import StudentIntake
from finance.models import Enrollment, Payment
from students.application.commands import StudentQuickCommand
from students.application.ports import StudentQuickAuditPort
from students.application.results import StudentQuickResult
from students.models import Student


class DjangoStudentQuickAudit(StudentQuickAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def _get_student(self, student_id: int):
        return Student.objects.get(pk=student_id)

    def _get_enrollment(self, enrollment_id: int | None):
        if enrollment_id is None:
            return None
        return Enrollment.objects.get(pk=enrollment_id)

    def _get_payment(self, payment_id: int | None):
        if payment_id is None:
            return None
        return Payment.objects.get(pk=payment_id)

    def _get_intake(self, intake_id: int | None):
        if intake_id is None:
            return None
        return StudentIntake.objects.get(pk=intake_id)

    def record_created(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        actor = self._get_actor(command.actor_id)
        student = self._get_student(result.student.id)
        payment = self._get_payment(result.enrollment_sync.payment_id)
        intake = self._get_intake(result.intake_id)

        log_audit_event(
            actor=actor,
            action='student_quick_created',
            target=student,
            description='Aluno criado pela tela leve de cadastro.',
            metadata={
                'status': student.status,
                'enrollment_id': result.enrollment_sync.enrollment_id,
                'payment_id': result.enrollment_sync.payment_id,
                'movement': result.enrollment_sync.movement,
                'intake_id': result.intake_id,
            },
        )
        if payment is not None:
            log_audit_event(
                actor=actor,
                action='student_quick_payment_created',
                target=payment,
                description='Primeira cobranca criada pela tela leve do aluno.',
                metadata={'status': payment.status, 'method': payment.method},
            )
        if intake is not None:
            log_audit_event(
                actor=actor,
                action='student_intake_converted',
                target=intake,
                description='Lead convertido em aluno pela tela leve.',
                metadata={'student_id': student.id},
            )

    def record_updated(self, *, command: StudentQuickCommand, result: StudentQuickResult) -> None:
        actor = self._get_actor(command.actor_id)
        student = self._get_student(result.student.id)
        enrollment = self._get_enrollment(result.enrollment_sync.enrollment_id)
        payment = self._get_payment(result.enrollment_sync.payment_id)
        intake = self._get_intake(result.intake_id)

        log_audit_event(
            actor=actor,
            action='student_quick_updated',
            target=student,
            description='Aluno alterado pela tela leve de cadastro.',
            metadata={
                'changed_fields': list(result.changed_fields),
                'enrollment_id': result.enrollment_sync.enrollment_id,
                'payment_id': result.enrollment_sync.payment_id,
                'movement': result.enrollment_sync.movement,
                'intake_id': result.intake_id,
            },
        )
        if enrollment is not None and result.enrollment_sync.movement in ('upgrade', 'downgrade', 'troca de plano'):
            log_audit_event(
                actor=actor,
                action='student_plan_changed',
                target=enrollment,
                description='Troca de plano registrada pela tela leve do aluno.',
                metadata={'movement': result.enrollment_sync.movement},
            )
        if payment is not None:
            log_audit_event(
                actor=actor,
                action='student_quick_payment_created',
                target=payment,
                description='Cobranca criada ou confirmada pela tela leve do aluno.',
                metadata={'status': payment.status, 'method': payment.method},
            )
        if intake is not None:
            log_audit_event(
                actor=actor,
                action='student_intake_converted',
                target=intake,
                description='Lead vinculado ao aluno pela tela leve.',
                metadata={'student_id': student.id},
            )


class DjangoStudentActionAudit:
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def record_payment_updated(self, *, actor_id: int | None, payment_id: int) -> None:
        actor = self._get_actor(actor_id)
        payment = Payment.objects.get(pk=payment_id)
        log_audit_event(
            actor=actor,
            action='student_payment_updated',
            target=payment,
            description='Cobranca atualizada pela tela do aluno.',
            metadata={'status': payment.status},
        )

    def record_payment_marked_paid(self, *, actor_id: int | None, payment_id: int) -> None:
        actor = self._get_actor(actor_id)
        payment = Payment.objects.get(pk=payment_id)
        log_audit_event(
            actor=actor,
            action='student_payment_marked_paid',
            target=payment,
            description='Cobranca confirmada como paga pela tela do aluno.',
            metadata={'method': payment.method},
        )

    def record_payment_refunded(self, *, actor_id: int | None, payment_id: int) -> None:
        actor = self._get_actor(actor_id)
        payment = Payment.objects.get(pk=payment_id)
        log_audit_event(
            actor=actor,
            action='student_payment_refunded',
            target=payment,
            description='Pagamento estornado pela tela do aluno.',
            metadata={},
        )

    def record_payment_canceled(self, *, actor_id: int | None, payment_id: int) -> None:
        actor = self._get_actor(actor_id)
        payment = Payment.objects.get(pk=payment_id)
        log_audit_event(
            actor=actor,
            action='student_payment_canceled',
            target=payment,
            description='Cobranca cancelada pela tela do aluno.',
            metadata={},
        )

    def record_payment_regenerated(self, *, actor_id: int | None, new_payment_id: int, previous_payment_id: int) -> None:
        actor = self._get_actor(actor_id)
        payment = Payment.objects.get(pk=new_payment_id)
        log_audit_event(
            actor=actor,
            action='student_payment_regenerated',
            target=payment,
            description='Nova cobranca gerada pela tela do aluno.',
            metadata={'previous_payment_id': previous_payment_id},
        )

    def record_enrollment_canceled(self, *, actor_id: int | None, enrollment_id: int, reason: str | None) -> None:
        actor = self._get_actor(actor_id)
        enrollment = Enrollment.objects.get(pk=enrollment_id)
        log_audit_event(
            actor=actor,
            action='student_enrollment_canceled',
            target=enrollment,
            description='Matricula cancelada pela tela do aluno.',
            metadata={'reason': reason},
        )

    def record_enrollment_reactivated(self, *, actor_id: int | None, enrollment_id: int, reason: str | None) -> None:
        actor = self._get_actor(actor_id)
        enrollment = Enrollment.objects.get(pk=enrollment_id)
        log_audit_event(
            actor=actor,
            action='student_enrollment_reactivated',
            target=enrollment,
            description='Matricula reativada pela tela do aluno.',
            metadata={'reason': reason},
        )


__all__ = ['DjangoStudentActionAudit', 'DjangoStudentQuickAudit']