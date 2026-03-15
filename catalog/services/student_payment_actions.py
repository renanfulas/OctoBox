"""Fachada publica das actions de pagamento do catalogo."""

from finance.models import Payment
from students.facade import run_student_payment_action


def handle_student_payment_action(*, actor, student, payment, action, payload=None):
	payload = payload or {}
	amount = payload.get('amount')
	if amount is None:
		amount = payment.amount
	result = run_student_payment_action(
		actor_id=getattr(actor, 'id', None),
		student_id=student.id,
		payment_id=payment.id,
		action=action,
		amount=amount,
		due_date=payload.get('due_date'),
		method=payload.get('method') or '',
		reference=payload.get('reference') or '',
		notes=payload.get('notes') or '',
	)
	if result.payment_id is None:
		return None
	return Payment.objects.get(pk=result.payment_id)


__all__ = ['handle_student_payment_action']