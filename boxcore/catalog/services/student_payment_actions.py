"""
ARQUIVO: handlers de acoes de pagamento do aluno no catalogo.

POR QUE ELE EXISTE:
- Explicita pelo nome do arquivo que esta camada resolve a acao publica handle_student_payment_action.

O QUE ESTE ARQUIVO FAZ:
1. Atualiza cobranca atual.
2. Marca pagamento, estorna, cancela e regenera cobranca.
3. Registra auditoria de cada movimento financeiro disparado pela operacao.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta a consistencia da trilha financeira do aluno.
"""

from django.utils import timezone

from boxcore.auditing import log_audit_event
from boxcore.models import PaymentStatus

from .payments import regenerate_payment


def handle_student_payment_action(*, actor, student, payment, action, payload=None):
    payload = payload or {}

    if action == 'update-payment':
        payment.amount = payload['amount']
        payment.due_date = payload['due_date']
        payment.method = payload['method']
        payment.reference = payload['reference']
        payment.notes = payload['notes']
        payment.save(update_fields=['amount', 'due_date', 'method', 'reference', 'notes', 'updated_at'])
        log_audit_event(
            actor=actor,
            action='student_payment_updated',
            target=payment,
            description='Cobranca atualizada pela tela do aluno.',
            metadata={'status': payment.status},
        )
        return payment

    if action == 'mark-paid':
        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at', 'updated_at'])
        log_audit_event(
            actor=actor,
            action='student_payment_marked_paid',
            target=payment,
            description='Cobranca confirmada como paga pela tela do aluno.',
            metadata={'method': payment.method},
        )
        return payment

    if action == 'refund-payment':
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=['status', 'updated_at'])
        log_audit_event(
            actor=actor,
            action='student_payment_refunded',
            target=payment,
            description='Pagamento estornado pela tela do aluno.',
            metadata={},
        )
        return payment

    if action == 'cancel-payment':
        payment.status = PaymentStatus.CANCELED
        payment.save(update_fields=['status', 'updated_at'])
        log_audit_event(
            actor=actor,
            action='student_payment_canceled',
            target=payment,
            description='Cobranca cancelada pela tela do aluno.',
            metadata={},
        )
        return payment

    if action == 'regenerate-payment':
        enrollment = payment.enrollment or student.enrollments.order_by('-start_date', '-created_at').first()
        new_payment = regenerate_payment(student=student, payment=payment, enrollment=enrollment)
        if new_payment is not None:
            log_audit_event(
                actor=actor,
                action='student_payment_regenerated',
                target=new_payment,
                description='Nova cobranca gerada pela tela do aluno.',
                metadata={'previous_payment_id': payment.id},
            )
        return new_payment

    return None