"""
ARQUIVO: apresentacao das cobrancas do aluno no Perfil (self-service, read-only).

POR QUE ELE EXISTE:
- O aluno nao via a propria situacao financeira no app (T2/T4). Aqui mora a
  transformacao das cobrancas do Student tenant em linhas simples para o Perfil,
  isolada da view para ficar testavel sem o runtime de sessao do student_app.

PONTOS CRITICOS:
- Roda no schema do box ativo (a view do aluno ja resolve o tenant).
- So as cobrancas DO PROPRIO aluno (student.payments).
"""

from django.utils import timezone

OPEN_STATUSES = ('pending', 'overdue')


def build_student_payment_rows(student, *, limit: int = 24, today=None) -> list[dict]:
    """Linhas das cobrancas do aluno (mais recentes primeiro) para o Perfil.

    PENDING vencida vira 'overdue' (apenas na apresentacao — o status persistido
    nao e alterado aqui).
    """
    from finance.models import PaymentStatus

    today = today or timezone.localdate()
    rows: list[dict] = []
    for payment in student.payments.order_by('-due_date', '-created_at')[:limit]:
        is_overdue = (
            payment.status == PaymentStatus.PENDING
            and payment.due_date is not None
            and payment.due_date < today
        )
        rows.append({
            'id': payment.id,
            'due_date': payment.due_date,
            'amount': payment.amount,
            'status': 'overdue' if is_overdue else payment.status,
            'status_label': 'Atrasado' if is_overdue else payment.get_status_display(),
            'is_open': (is_overdue or payment.status == PaymentStatus.PENDING),
            'paid_at': payment.paid_at,
        })
    return rows


def count_open_payments(rows: list[dict]) -> int:
    """Quantas cobrancas estao em aberto (pendente ou atrasada)."""
    return sum(1 for row in rows if row['status'] in OPEN_STATUSES)


def resolve_payable_student_invoice(student, payment_id):
    """Resolve a fatura que o aluno pode pagar, ou None.

    Seguranca: so retorna a cobranca se ela for DO PROPRIO aluno e estiver EM
    ABERTO (pendente/atrasada). Qualquer outro caso (fatura de outro aluno, paga,
    cancelada, estornada, inexistente) retorna None — a view trata como negado.
    """
    from finance.models import Payment, PaymentStatus

    payment = Payment.objects.filter(pk=payment_id, student=student).first()
    if payment is None:
        return None
    if payment.status not in (PaymentStatus.PENDING, PaymentStatus.OVERDUE):
        return None
    return payment


__all__ = [
    'build_student_payment_rows',
    'count_open_payments',
    'resolve_payable_student_invoice',
    'OPEN_STATUSES',
]
