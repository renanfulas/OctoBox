"""Fachada publica dos helpers de intake do catalogo."""

from communications.models import StudentIntake
from students.facade import run_student_intake_sync


def sync_student_intake(*, student, intake=None):
	result = run_student_intake_sync(
		student_id=student.id,
		intake_record_id=getattr(intake, 'id', None),
	)
	if result.intake_id is None:
		return None
	return StudentIntake.objects.get(pk=result.intake_id)


__all__ = ['sync_student_intake']