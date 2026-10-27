from __future__ import annotations

from django.db import OperationalError, ProgrammingError, transaction
from django.utils import timezone

from students.models import Student
from student_app.models import StudentAppActivity


def record_student_app_activity(
    *,
    student: Student,
    kind: str,
    source_object_id: int | None = None,
    metadata: dict | None = None,
    identity_id: int | None = None,
):
    try:
        with transaction.atomic():
            activity = StudentAppActivity.objects.create(
                student=student,
                kind=kind,
                activity_date=timezone.localdate(),
                source_object_id=source_object_id,
                metadata=metadata or {},
            )
            from student_identity.cohort_milestones import record_authenticated_student_return
            record_authenticated_student_return(
                identity_id=identity_id,
                occurred_at=activity.created_at,
                activity_kind=kind,
            )
            return activity
    except (OperationalError, ProgrammingError):
        return None
