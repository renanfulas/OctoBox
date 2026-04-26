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
from student_app.application.timezone import resolve_box_timezone


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

        box_timezone = resolve_box_timezone(box_root_slug=student.app_identity.box_root_slug)
        now = timezone.localtime(timezone.now(), box_timezone)
        session_local = timezone.localtime(session.scheduled_at, box_timezone)
        booking_horizon = now.date() + timedelta(days=1)
        if session_local.date() > booking_horizon:
            raise AttendanceNotAvailableError('Voce pode reservar apenas aulas de hoje ou amanha.')

        active_reservations = (
            Attendance.objects.select_for_update()
            .filter(
                student=student,
                status__in=[AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT],
            )
        )
        for active_attendance in active_reservations.select_related('session'):
            if active_attendance.session_id == session.id:
                continue
            active_session = active_attendance.session
            active_start = timezone.localtime(active_session.scheduled_at, box_timezone)
            active_end = active_start + timedelta(minutes=active_session.duration_minutes or 60)
            if active_end > now:
                raise AttendanceNotAvailableError(
                    'Voce ja tem uma reserva ativa. So pode reservar a proxima aula depois que a atual terminar.'
                )

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
