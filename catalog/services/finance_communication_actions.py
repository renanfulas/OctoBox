"""Fachada publica das actions de comunicacao financeira do catalogo."""

from communications.facade import run_finance_communication_action
from communications.models import WhatsAppMessageLog
from finance.follow_up_tracker import mark_finance_follow_up_realized
from shared_support.whatsapp_links import build_whatsapp_message_href
from students.models import Student


def handle_finance_communication_action(*, actor, action_kind, student_id, payment_id=None, enrollment_id=None):
	result = run_finance_communication_action(
		actor_id=getattr(actor, 'id', None),
		action_kind=action_kind,
		student_id=student_id,
		payment_id=payment_id,
		enrollment_id=enrollment_id,
	)
	
	student = Student.objects.get(pk=result.student_id)
	
	# Se estiver bloqueado, retornamos o LOG QUE BLOQUEOU (mensagem
	# previa enviada dentro da janela de repeat-block). Antes retornavamos
	# None — quebrava callers que precisam comparar IDs (test_finance_
	# communication_handler_blocks_duplicate_same_day_message).
	message = WhatsAppMessageLog.objects.filter(pk=result.message_log_id).first() if result.message_log_id else None

	if result.blocked:
		return {
			'student': student,
			'message': message,
			'blocked': True,
			'whatsapp_href': None,
		}
	mark_finance_follow_up_realized(
		student_id=result.student_id,
		action_kind=action_kind,
		actor_id=getattr(actor, 'id', None),
		payment_id=payment_id,
		enrollment_id=enrollment_id,
	)
	return {
		'student': student,
		'message': message,
		'blocked': False,
		'whatsapp_href': build_whatsapp_message_href(
			phone=getattr(message.contact, 'phone', '') or getattr(student, 'phone', ''),
			message=message.body,
		),
	}


__all__ = ['handle_finance_communication_action']
