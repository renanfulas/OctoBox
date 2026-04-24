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
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from students.models import Student


class AttendanceNotAvailableError(Exception):
    """Levanta quando a aula nao pode ser reservada pelo app do aluno."""


@dataclass(frozen=True)
class AttendanceConfirmationResult:
    session: ClassSession
    attendance: Attendance
    created: bool
    reactivated: bool


@dataclass(frozen=True)
class AttendanceCancelResult:
    session: ClassSession
    attendance: Attendance


def confirm_student_attendance(*, student, session_id) -> AttendanceConfirmationResult:
    with transaction.atomic():
        Student.objects.select_for_update().filter(pk=student.pk).get()
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

        same_day_active = (
            Attendance.objects.select_for_update()
            .filter(
                student=student,
                session__scheduled_at__date=session.scheduled_at.date(),
                status__in=[AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN],
            )
            .exclude(session=session)
            .exists()
        )
        if same_day_active:
            raise AttendanceNotAvailableError('Voce ja tem uma reserva ativa neste dia.')

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


def cancel_student_attendance(*, student, session_id) -> AttendanceCancelResult:
    session = (
        ClassSession.objects.select_related('coach')
        .filter(
            pk=session_id,
            status__in=[SessionStatus.SCHEDULED, SessionStatus.OPEN],
        )
        .first()
    )
    if session is None:
        raise AttendanceNotAvailableError('Sessao indisponivel para cancelamento.')

    cancel_deadline = session.scheduled_at - timedelta(hours=1)
    if timezone.now() > cancel_deadline:
        raise AttendanceNotAvailableError('Cancelamento encerrado para esta aula.')

    attendance = (
        Attendance.objects
        .filter(student=student, session=session)
        .first()
    )
    if attendance is None:
        raise AttendanceNotAvailableError('Reserva indisponivel para cancelamento.')
    if attendance.status == AttendanceStatus.CHECKED_IN:
        raise AttendanceNotAvailableError('Sua presenca ja foi confirmada nesta aula.')
    if attendance.status != AttendanceStatus.BOOKED:
        raise AttendanceNotAvailableError('Reserva indisponivel para cancelamento.')

    attendance.status = AttendanceStatus.CANCELED
    attendance.save(update_fields=['status', 'updated_at'])

    return AttendanceCancelResult(
        session=session,
        attendance=attendance,
    )
