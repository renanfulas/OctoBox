"""Fachada publica das actions de comunicacao financeira do catalogo."""

from communications.facade import run_finance_communication_action
from communications.models import WhatsAppMessageLog
from students.models import Student


def handle_finance_communication_action(*, actor, payload):
	result = run_finance_communication_action(
		actor_id=getattr(actor, 'id', None),
		action_kind=payload.get('action_kind') or '',
		student_id=int(payload.get('student_id')),
		payment_id=int(payload.get('payment_id')) if payload.get('payment_id') else None,
		enrollment_id=int(payload.get('enrollment_id')) if payload.get('enrollment_id') else None,
	)
	return {
		'student': Student.objects.get(pk=result.student_id),
		'message': WhatsAppMessageLog.objects.get(pk=result.message_log_id),
	}


__all__ = ['handle_finance_communication_action']