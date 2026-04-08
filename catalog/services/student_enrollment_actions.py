"""Fachada publica das actions de matricula do catalogo."""

from finance.models import Enrollment
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.student_event_stream import publish_student_stream_event
from shared_support.student_snapshot_versions import build_student_snapshot_version
from students.facade import run_student_enrollment_action


def handle_student_enrollment_action(*, actor, student, enrollment, action, action_date, reason=''):
	result = run_student_enrollment_action(
		actor_id=getattr(actor, 'id', None),
		student_id=student.id,
		enrollment_id=enrollment.id,
		action=action,
		action_date=action_date,
		reason=reason,
	)
	if result.enrollment_id is None:
		return None
	updated_enrollment = Enrollment.objects.get(pk=result.enrollment_id)
	publish_student_stream_event(
		student_id=student.id,
		event_type='student.enrollment.updated',
		snapshot_version=build_student_snapshot_version(
			student=student,
			latest_enrollment=updated_enrollment,
		),
		meta={
			'action': action,
			'enrollment_id': updated_enrollment.id,
			'status': updated_enrollment.status,
		},
	)
	publish_manager_stream_event(
		event_type='student.enrollment.updated',
		meta={
			'student_id': student.id,
			'action': action,
			'enrollment_id': updated_enrollment.id,
			'status': updated_enrollment.status,
		},
	)
	return updated_enrollment


__all__ = ['handle_student_enrollment_action']
