"""Fachada publica das actions de comunicacao financeira do catalogo."""

from communications.facade import run_finance_communication_action
from communications.models import WhatsAppMessageLog
from students.models import Student


def handle_finance_communication_action(*, actor, action_kind, student_id, payment_id=None, enrollment_id=None):
	result = run_finance_communication_action(
		actor_id=getattr(actor, 'id', None),
		action_kind=action_kind,
		student_id=student_id,
		payment_id=payment_id,
		enrollment_id=enrollment_id,
	)
	return {
		'student': Student.objects.get(pk=result.student_id),
		'message': WhatsAppMessageLog.objects.get(pk=result.message_log_id),
	}


__all__ = ['handle_finance_communication_action']