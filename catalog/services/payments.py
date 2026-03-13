"""Fachada publica dos helpers de pagamento do catalogo."""

from finance.models import Payment
from students.application.payment_terms import advance_due_date, shift_month
from students.facade import run_student_payment_regeneration, run_student_payment_schedule


def create_payment_schedule(
	*,
	student,
	enrollment,
	due_date,
	payment_method,
	confirm_payment_now,
	note,
	amount,
	reference,
	billing_strategy,
	installment_total,
	recurrence_cycles,
):
	result = run_student_payment_schedule(
		student_id=student.id,
		enrollment_id=getattr(enrollment, 'id', None),
		due_date=due_date,
		payment_method=payment_method,
		confirm_payment_now=confirm_payment_now,
		note=note,
		amount=amount,
		reference=reference,
		billing_strategy=billing_strategy,
		installment_total=installment_total,
		recurrence_cycles=recurrence_cycles,
	)
	return Payment.objects.get(pk=result.payment_id)


def regenerate_payment(*, student, payment, enrollment=None):
	result = run_student_payment_regeneration(
		student_id=student.id,
		payment_id=payment.id,
		enrollment_id=getattr(enrollment, 'id', None),
	)
	if result.payment_id is None:
		return None
	return Payment.objects.get(pk=result.payment_id)


__all__ = ['advance_due_date', 'create_payment_schedule', 'regenerate_payment', 'shift_month']