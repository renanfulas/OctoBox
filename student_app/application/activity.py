from __future__ import annotations

from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from students.models import Student
from student_app.models import StudentAppActivity


def record_student_app_activity(*, student: Student, kind: str, source_object_id: int | None = None, metadata: dict | None = None):
    try:
        return StudentAppActivity.objects.create(
            student=student,
            kind=kind,
            activity_date=timezone.localdate(),
            source_object_id=source_object_id,
            metadata=metadata or {},
        )
    except (OperationalError, ProgrammingError):
        return None
