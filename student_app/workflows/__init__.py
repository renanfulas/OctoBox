"""
ARQUIVO: fachada publica dos workflows do app do aluno.

POR QUE ELE EXISTE:
- oferece um ponto unico para importar escritas mais densas do student_app sem acoplar views a detalhes internos.
"""

from .attendance_workflows import (
    AttendanceCancelResult,
    AttendanceConfirmationResult,
    AttendanceNotAvailableError,
    cancel_student_attendance,
    confirm_student_attendance,
)
from .onboarding_workflows import OnboardingCompletionResult, OnboardingWorkflow

__all__ = [
    'AttendanceCancelResult',
    'AttendanceConfirmationResult',
    'AttendanceNotAvailableError',
    'OnboardingCompletionResult',
    'OnboardingWorkflow',
    'cancel_student_attendance',
    'confirm_student_attendance',
]
