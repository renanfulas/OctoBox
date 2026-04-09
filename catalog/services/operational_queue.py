"""Fachada publica da fila operacional do catalogo."""

from communications.facade import run_build_operational_queue_snapshot
from communications.models import WhatsAppContact
from finance.models import Enrollment, Payment
from shared_support.whatsapp_contact_state import build_whatsapp_contact_state
from shared_support.whatsapp_links import build_whatsapp_message_href
from students.models import Student


def build_operational_queue_snapshot(*, limit=9):
	result = run_build_operational_queue_snapshot(limit=limit)
	student_ids = {item.student_id for item in result.items}
	payment_ids = {item.payment_id for item in result.items if item.payment_id is not None}
	enrollment_ids = {item.enrollment_id for item in result.items if item.enrollment_id is not None}

	students_by_id = Student.objects.in_bulk(student_ids)
	payments_by_id = Payment.objects.select_related('enrollment__plan', 'student').in_bulk(payment_ids)
	enrollments_by_id = Enrollment.objects.select_related('student', 'plan').in_bulk(enrollment_ids)
	contacts_by_student_id = {
		contact.linked_student_id: contact
		for contact in WhatsAppContact.objects.filter(linked_student_id__in=student_ids)
	}

	queue = []
	for item in result.items:
		student = students_by_id.get(item.student_id)
		contact_state = build_whatsapp_contact_state(contacts_by_student_id.get(item.student_id))
		queue_item = {
			'kind': item.kind,
			'title': item.title,
			'student': student,
			'payment': payments_by_id.get(item.payment_id),
			'enrollment': enrollments_by_id.get(item.enrollment_id),
			'pill': item.pill,
			'pill_class': item.pill_class,
			'summary': item.summary,
			'suggested_message': item.suggested_message,
			'whatsapp_href': build_whatsapp_message_href(
				phone=getattr(student, 'phone', ''),
				message=item.suggested_message,
			),
			**contact_state,
		}
		if queue_item['whatsapp_repeat_blocked']:
			continue
		queue.append(queue_item)
	return queue


def build_operational_queue_metrics(queue):
	return {
		'Vencendo nos proximos dias': sum(1 for item in queue if item['kind'] == 'upcoming'),
		'Cobrancas em atraso': sum(1 for item in queue if item['kind'] == 'overdue'),
		'Chance de reativacao': sum(1 for item in queue if item['kind'] == 'reactivation'),
	}


build_operational_queue = build_operational_queue_snapshot
summarize_operational_queue = build_operational_queue_metrics


__all__ = [
	'build_operational_queue',
	'build_operational_queue_metrics',
	'build_operational_queue_snapshot',
	'summarize_operational_queue',
]
