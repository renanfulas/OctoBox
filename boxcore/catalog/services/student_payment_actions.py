"""
ARQUIVO: fachada das actions de pagamento do aluno.

POR QUE ELE EXISTE:
- Mantem a interface publica atual enquanto o fluxo real de pagamento sai para command, use case e adapter Django.

O QUE ESTE ARQUIVO FAZ:
1. Traduz parametros legados para um command explicito.
2. Chama o use case concreto do dominio.
3. Devolve o model historico esperado pelas views e testes.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar auditoria, ORM ou transacao.
"""

from students.application.commands import StudentPaymentActionCommand
from students.infrastructure import execute_student_payment_action_command

from finance.models import Payment


def handle_student_payment_action(*, actor, student, payment, action, payload=None):
    payload = payload or {}
    command = StudentPaymentActionCommand(
        actor_id=getattr(actor, 'id', None),
        student_id=student.id,
        payment_id=payment.id,
        action=action,
        amount=payload.get('amount'),
        due_date=payload.get('due_date'),
        method=payload.get('method') or '',
        reference=payload.get('reference') or '',
        notes=payload.get('notes') or '',
    )
    result = execute_student_payment_action_command(command)
    if result.payment_id is None:
        return None
    return Payment.objects.get(pk=result.payment_id)