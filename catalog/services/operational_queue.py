"""Fachada publica da fila operacional do catalogo."""

from communications.facade import run_build_operational_queue_snapshot
from finance.models import Enrollment, Payment
from students.models import Student


def build_operational_queue_snapshot(*, limit=9):
	result = run_build_operational_queue_snapshot(limit=limit)
	student_ids = {item.student_id for item in result.items}
	payment_ids = {item.payment_id for item in result.items if item.payment_id is not None}
	enrollment_ids = {item.enrollment_id for item in result.items if item.enrollment_id is not None}

	students_by_id = Student.objects.in_bulk(student_ids)
	payments_by_id = Payment.objects.select_related('enrollment__plan', 'student').in_bulk(payment_ids)
	enrollments_by_id = Enrollment.objects.select_related('student', 'plan').in_bulk(enrollment_ids)

	queue = []
	for item in result.items:
		queue.append(
			{
				'kind': item.kind,
				'title': item.title,
				'student': students_by_id.get(item.student_id),
				'payment': payments_by_id.get(item.payment_id),
				'enrollment': enrollments_by_id.get(item.enrollment_id),
				'pill': item.pill,
				'pill_class': item.pill_class,
				'summary': item.summary,
				'suggested_message': item.suggested_message,
			}
		)
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