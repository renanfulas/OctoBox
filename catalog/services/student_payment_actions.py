"""Fachada publica das actions de pagamento do catalogo."""

from finance.models import Payment
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.student_event_stream import publish_student_stream_event
from shared_support.student_snapshot_versions import build_student_snapshot_version
from students.facade import run_student_payment_action, run_student_payment_schedule


def handle_student_payment_creation(*, actor, student, payload):
	from django.utils import timezone
	
	result = run_student_payment_schedule(
		student_id=student.id,
		enrollment_id=None,
		due_date=timezone.localdate(),
		payment_method=payload.get('method', 'pix'),
		confirm_payment_now=True,  # 1-Clique Terminal: assumir pago de imediato na criacao avulsa
		note=payload.get('notes', 'Cobrança Avulsa Gerada no Balcão'),
		amount=payload.get('amount'),
		reference=payload.get('reference', ''),
		billing_strategy='single',
		installment_total=1,
		recurrence_cycles=1,
	)
	if result.payment_id is None:
		return None
	payment = Payment.objects.get(pk=result.payment_id)
	publish_student_stream_event(
		student_id=student.id,
		event_type='student.payment.updated',
		snapshot_version=build_student_snapshot_version(
			student=student,
			latest_enrollment=payment.enrollment,
			latest_payment=payment,
		),
		meta={
			'action': 'create-payment',
			'payment_id': payment.id,
			'status': payment.status,
		},
	)
	publish_manager_stream_event(
		event_type='student.payment.updated',
		meta={
			'student_id': student.id,
			'action': 'create-payment',
			'payment_id': payment.id,
			'status': payment.status,
		},
	)
	return payment


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
	updated_payment = Payment.objects.get(pk=result.payment_id)
	publish_student_stream_event(
		student_id=student.id,
		event_type='student.payment.updated',
		snapshot_version=build_student_snapshot_version(
			student=student,
			latest_enrollment=updated_payment.enrollment,
			latest_payment=updated_payment,
		),
		meta={
			'action': action,
			'payment_id': updated_payment.id,
			'status': updated_payment.status,
		},
	)
	publish_manager_stream_event(
		event_type='student.payment.updated',
		meta={
			'student_id': student.id,
			'action': action,
			'payment_id': updated_payment.id,
			'status': updated_payment.status,
		},
	)
	return updated_payment


__all__ = ['handle_student_payment_action', 'handle_student_payment_creation']
