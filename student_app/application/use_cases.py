from __future__ import annotations

from decimal import Decimal

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, ClassSession

from student_app.application.results import (
    StudentDashboardResult,
    StudentSessionCard,
    WorkoutPrescriptionResult,
)
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.models import StudentExerciseMax


class GetStudentDashboard:
    def execute(self, *, identity) -> StudentDashboardResult:
        sessions = (
            ClassSession.objects.filter(status__in=['scheduled', 'open'])
            .order_by('scheduled_at')
            .prefetch_related('attendances', 'coach')[:5]
        )
        attendance_by_session = {
            attendance.session_id: attendance
            for attendance in Attendance.objects.filter(student=identity.student, session__in=sessions).select_related('session')
        }
        next_sessions = tuple(
            StudentSessionCard(
                title=session.title,
                scheduled_label=session.scheduled_at.strftime('%d/%m %H:%M'),
                coach_name=session.coach.get_full_name() if session.coach else 'Equipe OctoBox',
                attendance_status=(attendance_by_session.get(session.id).get_status_display() if attendance_by_session.get(session.id) else 'Sem reserva'),
                notes=session.notes,
            )
            for session in sessions
        )
        enrollment = (
            Enrollment.objects.select_related('plan')
            .filter(student=identity.student, status=EnrollmentStatus.ACTIVE)
            .order_by('-created_at')
            .first()
        )
        membership_label = enrollment.plan.name if enrollment and enrollment.plan_id else 'Sem plano ativo'
        return StudentDashboardResult(
            student_name=identity.student.full_name,
            box_root_slug=identity.box_root_slug,
            next_sessions=next_sessions,
            membership_label=membership_label,
        )


class GetStudentWorkoutPrescription:
    def execute(self, *, student, exercise_slug: str, percentage: Decimal) -> WorkoutPrescriptionResult | None:
        exercise_max = (
            StudentExerciseMax.objects.filter(student=student, exercise_slug=exercise_slug)
            .order_by('-updated_at')
            .first()
        )
        if exercise_max is None:
            return None
        prescription = build_workout_prescription(
            one_rep_max_kg=exercise_max.one_rep_max_kg,
            percentage=percentage,
        )
        return WorkoutPrescriptionResult(
            exercise_label=exercise_max.exercise_label,
            percentage_label=f'{percentage}%',
            one_rep_max_label=f'{exercise_max.one_rep_max_kg} kg',
            raw_load_label=f'{prescription.raw_load_kg} kg',
            rounded_load_label=f'{prescription.rounded_load_kg} kg',
            observation=prescription.observation,
        )
