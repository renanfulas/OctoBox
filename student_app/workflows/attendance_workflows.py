"""
ARQUIVO: workflows de presenca do app do aluno.

POR QUE ELE EXISTE:
- tira da view a regra de escrita para confirmar ou reativar presenca em aula.

O QUE ESTE ARQUIVO FAZ:
1. localiza a sessao elegivel para reserva pelo aluno.
2. cria ou reativa a reserva com a origem correta.
"""

from __future__ import annotations

from dataclasses import dataclass

from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus


class AttendanceNotAvailableError(Exception):
    """Levanta quando a aula nao pode ser reservada pelo app do aluno."""


@dataclass(frozen=True)
class AttendanceConfirmationResult:
    session: ClassSession
    attendance: Attendance
    created: bool
    reactivated: bool


def confirm_student_attendance(*, student, session_id) -> AttendanceConfirmationResult:
    session = (
        ClassSession.objects.select_related('coach')
        .filter(
            pk=session_id,
            status__in=[SessionStatus.SCHEDULED, SessionStatus.OPEN],
        )
        .first()
    )
    if session is None:
        raise AttendanceNotAvailableError('Sessao indisponivel para reserva.')

    attendance, created = Attendance.objects.get_or_create(
        student=student,
        session=session,
        defaults={
            'status': AttendanceStatus.BOOKED,
            'reservation_source': 'student_app',
        },
    )
    reactivated = False
    if not created and attendance.status in {AttendanceStatus.ABSENT, AttendanceStatus.CANCELED}:
        attendance.status = AttendanceStatus.BOOKED
        attendance.reservation_source = 'student_app'
        attendance.save(update_fields=['status', 'reservation_source', 'updated_at'])
        reactivated = True

    return AttendanceConfirmationResult(
        session=session,
        attendance=attendance,
        created=created,
        reactivated=reactivated,
    )
