"""Fachada publica das actions de matricula do catalogo."""

from finance.models import Enrollment
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
	return Enrollment.objects.get(pk=result.enrollment_id)


__all__ = ['handle_student_enrollment_action']