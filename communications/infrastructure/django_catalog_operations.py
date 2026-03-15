"""
ARQUIVO: adapters Django do bloco operacional/comercial do catálogo.

POR QUE ELE EXISTE:
- Remove do catálogo legado a orquestração de fila operacional e da ação de comunicação financeira.

O QUE ESTE ARQUIVO FAZ:
1. Resolve a ação financeira para aluno, pagamento e matrícula.
2. Monta o snapshot da fila operacional com queries Django.
3. Reaproveita o use case de mensagem operacional já desacoplado.

PONTOS CRITICOS:
- Este arquivo é a única camada aqui que deve conhecer ORM para esse bloco do catálogo.
"""

from datetime import timedelta

from communications.application.commands import BuildOperationalQueueSnapshotCommand, FinanceCommunicationActionCommand, RegisterOperationalMessageCommand
from communications.application.message_templates import build_operational_message_body
from communications.application.ports import ClockPort, FinanceCommunicationActionPort, OperationalQueueSnapshotPort
from communications.application.results import (
    FinanceCommunicationActionResult,
    OperationalQueueItemResult,
    OperationalQueueSnapshotResult,
)
from communications.application.use_cases import (
    execute_build_operational_queue_snapshot_use_case,
    execute_finance_communication_action_use_case,
)
from communications.infrastructure.django_clock import DjangoClockPort
from communications.infrastructure.django_use_cases import execute_register_operational_message_command
from communications.models import WhatsAppMessageLog
from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus
from students.models import Student


class DjangoFinanceCommunicationActionPort(FinanceCommunicationActionPort):
    def execute(self, command: FinanceCommunicationActionCommand) -> FinanceCommunicationActionResult:
        student = Student.objects.get(pk=command.student_id)
        payment = Payment.objects.filter(pk=command.payment_id, student=student).first() if command.payment_id else None
        enrollment = Enrollment.objects.filter(pk=command.enrollment_id, student=student).first() if command.enrollment_id else None
        message_result = execute_register_operational_message_command(
            RegisterOperationalMessageCommand(
                actor_id=command.actor_id,
                action_kind=command.action_kind,
                student_id=student.id,
                payment_id=getattr(payment, 'id', None),
                enrollment_id=getattr(enrollment, 'id', None),
            )
        )
        return FinanceCommunicationActionResult(
            student_id=student.id,
            message_log_id=message_result.message_log_id,
            blocked=message_result.blocked,
        )


class DjangoOperationalQueueSnapshotPort(OperationalQueueSnapshotPort):
    def __init__(self, *, clock: ClockPort):
        self.clock = clock

    def build_snapshot(self, command: BuildOperationalQueueSnapshotCommand) -> OperationalQueueSnapshotResult:
        today = self.clock.today()
        soon_threshold = today + timedelta(days=3)

        upcoming_payments = list(
            Payment.objects.select_related('student', 'enrollment__plan')
            .filter(status=PaymentStatus.PENDING, due_date__gte=today, due_date__lte=soon_threshold)
            .order_by('due_date', 'student__full_name')[:3]
        )
        overdue_payments = list(
            Payment.objects.select_related('student', 'enrollment__plan')
            .filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE], due_date__lt=today)
            .order_by('due_date', 'student__full_name')[:3]
        )
        for payment in overdue_payments:
            if payment.status == PaymentStatus.PENDING and payment.due_date < today:
                payment.status = PaymentStatus.OVERDUE

        reactivation_candidates = list(
            Enrollment.objects.select_related('student', 'plan')
            .filter(status__in=[EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED], end_date__isnull=False)
            .order_by('-end_date', '-updated_at')[:3]
        )

        items = []
        for payment in upcoming_payments:
            items.append(
                OperationalQueueItemResult(
                    kind='upcoming',
                    title='Lembrete de vencimento',
                    student_id=payment.student_id,
                    payment_id=payment.id,
                    enrollment_id=payment.enrollment_id,
                    pill='Vence em breve',
                    pill_class='',
                    summary=f'{payment.student.full_name} | vence em {payment.due_date:%d/%m/%Y} | R$ {payment.amount:.2f}',
                    suggested_message=build_operational_message_body(
                        action_kind='upcoming',
                        first_name=payment.student.full_name.split()[0],
                        payment_due_date=payment.due_date,
                        payment_amount=payment.amount,
                    ),
                )
            )
        for payment in overdue_payments:
            items.append(
                OperationalQueueItemResult(
                    kind='overdue',
                    title='Cobranca em atraso',
                    student_id=payment.student_id,
                    payment_id=payment.id,
                    enrollment_id=payment.enrollment_id,
                    pill='Atrasado',
                    pill_class='warning',
                    summary=f'{payment.student.full_name} | venceu em {payment.due_date:%d/%m/%Y} | R$ {payment.amount:.2f}',
                    suggested_message=build_operational_message_body(
                        action_kind='overdue',
                        first_name=payment.student.full_name.split()[0],
                        payment_due_date=payment.due_date,
                        payment_amount=payment.amount,
                    ),
                )
            )
        for enrollment in reactivation_candidates:
            items.append(
                OperationalQueueItemResult(
                    kind='reactivation',
                    title='Tentativa de reativacao',
                    student_id=enrollment.student_id,
                    payment_id=None,
                    enrollment_id=enrollment.id,
                    pill='Retencao',
                    pill_class='info',
                    summary=f'{enrollment.student.full_name} | plano {enrollment.plan.name} | fim em {enrollment.end_date:%d/%m/%Y}',
                    suggested_message=build_operational_message_body(
                        action_kind='reactivation',
                        first_name=enrollment.student.full_name.split()[0],
                        plan_name=enrollment.plan.name,
                    ),
                )
            )
        return OperationalQueueSnapshotResult(items=tuple(items[: command.limit]))


def execute_finance_communication_action_command(command: FinanceCommunicationActionCommand):
    return execute_finance_communication_action_use_case(
        command,
        finance_action_port=DjangoFinanceCommunicationActionPort(),
    )


def execute_build_operational_queue_snapshot_command(command: BuildOperationalQueueSnapshotCommand):
    return execute_build_operational_queue_snapshot_use_case(
        command,
        snapshot_port=DjangoOperationalQueueSnapshotPort(clock=DjangoClockPort()),
    )


def get_message_log(message_log_id: int):
    return WhatsAppMessageLog.objects.get(pk=message_log_id)


__all__ = [
    'execute_build_operational_queue_snapshot_command',
    'execute_finance_communication_action_command',
    'get_message_log',
]