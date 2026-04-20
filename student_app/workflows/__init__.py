"""
ARQUIVO: fachada publica dos workflows do app do aluno.

POR QUE ELE EXISTE:
- oferece um ponto unico para importar escritas mais densas do student_app sem acoplar views a detalhes internos.
"""

from .attendance_workflows import AttendanceConfirmationResult, AttendanceNotAvailableError, confirm_student_attendance
from .onboarding_workflows import OnboardingCompletionResult, OnboardingWorkflow

__all__ = [
    'AttendanceConfirmationResult',
    'AttendanceNotAvailableError',
    'OnboardingCompletionResult',
    'OnboardingWorkflow',
    'confirm_student_attendance',
]
