"""Signals for durable facts emitted by staff attendance actions."""

from django.dispatch import Signal


# Sent synchronously inside the attendance action's transaction, after the
# persisted row acquires its first check-in timestamp. Consumers may persist
# tenant-local facts without making operations depend on student_identity.
student_attendance_checked_in = Signal()


__all__ = ['student_attendance_checked_in']
