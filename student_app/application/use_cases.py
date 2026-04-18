from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.application.results import (
    StudentDashboardResult,
    StudentSessionCard,
    StudentWorkoutBlockCard,
    StudentWorkoutDayResult,
    StudentWorkoutMovementCard,
    WorkoutPrescriptionResult,
)
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.models import SessionWorkout, SessionWorkoutStatus, StudentExerciseMax, WorkoutLoadType


def _movement_value(movement, field_name):
    if isinstance(movement, dict):
        return movement.get(field_name)
    return getattr(movement, field_name, None)


def build_student_prescription_label(*, movement):
    bits = []
    sets = _movement_value(movement, 'sets')
    reps = _movement_value(movement, 'reps')
    load_type = _movement_value(movement, 'load_type')
    load_value = _movement_value(movement, 'load_value')
    if sets:
        bits.append(f'{sets} series')
    if reps:
        bits.append(f'{reps} reps')
    if load_type == WorkoutLoadType.PERCENTAGE_OF_RM and load_value is not None:
        bits.append(f'@ {load_value}% do RM')
    elif load_type == WorkoutLoadType.FIXED_KG and load_value is not None:
        bits.append(f'@ {load_value} kg')
    elif load_type == WorkoutLoadType.FREE:
        bits.append('carga livre')
    return ' · '.join(bits) or 'Sem detalhe de prescricao'


def build_student_recommendation_preview(*, movement, student=None):
    load_type = _movement_value(movement, 'load_type')
    load_value = _movement_value(movement, 'load_value')
    movement_slug = _movement_value(movement, 'movement_slug')
    if load_type == WorkoutLoadType.PERCENTAGE_OF_RM and load_value is not None:
        if student is not None:
            exercise_max = (
                StudentExerciseMax.objects.filter(student=student, exercise_slug=movement_slug)
                .order_by('-updated_at')
                .first()
            )
            if exercise_max is not None:
                prescription = build_workout_prescription(
                    one_rep_max_kg=exercise_max.one_rep_max_kg,
                    percentage=load_value,
                )
                return (
                    'Percentual do RM',
                    prescription.rounded_load_kg,
                    f'Baseado no seu RM atual de {exercise_max.one_rep_max_kg} kg.',
                )
            return (
                'Percentual do RM',
                None,
                'Registre seu RM deste movimento para receber a carga recomendada aqui.',
            )
        return (
            'Percentual do RM',
            None,
            'O aluno vera a carga recomendada aqui quando tiver RM registrado para este movimento.',
        )
    if load_type == WorkoutLoadType.FIXED_KG and load_value is not None:
        return (
            'Carga fixa',
            load_value,
            'Esse bloco ja chega ao aluno com uma carga fechada definida pelo coach.',
        )
    return (
        'Carga livre',
        None,
        'O aluno vera a orientacao de ajuste livre com base na leitura de esforco e do coach.',
    )


class GetStudentDashboard:
    wod_window_before_minutes = 30
    wod_window_after_minutes = 30

    def _resolve_home_mode(self, *, session_cards, now):
        for session_card in session_cards:
            if session_card.attendance_code not in {
                AttendanceStatus.BOOKED,
                AttendanceStatus.CHECKED_IN,
                AttendanceStatus.CHECKED_OUT,
            }:
                continue
            starts_at = session_card.scheduled_at - timedelta(minutes=self.wod_window_before_minutes)
            ends_at = session_card.scheduled_at + timedelta(minutes=60 + self.wod_window_after_minutes)
            if starts_at <= now <= ends_at:
                return 'wod_active', session_card
        return 'schedule_default', None

    def execute(self, *, identity) -> StudentDashboardResult:
        now = timezone.localtime()
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
                session_id=session.id,
                title=session.title,
                scheduled_label=session.scheduled_at.strftime('%d/%m %H:%M'),
                scheduled_at=session.scheduled_at,
                coach_name=session.coach.get_full_name() if session.coach else 'Equipe OctoBox',
                attendance_status=(attendance_by_session.get(session.id).get_status_display() if attendance_by_session.get(session.id) else 'Sem reserva'),
                attendance_code=(attendance_by_session.get(session.id).status if attendance_by_session.get(session.id) else ''),
                notes=session.notes,
                can_confirm_presence=(
                    attendance_by_session.get(session.id) is None
                    or attendance_by_session.get(session.id).status in {
                        AttendanceStatus.ABSENT,
                        AttendanceStatus.CANCELED,
                    }
                ),
            )
            for session in sessions
        )
        home_mode, active_wod_session = self._resolve_home_mode(session_cards=next_sessions, now=now)
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
            home_mode=home_mode,
            focal_session=next_sessions[0] if next_sessions else None,
            active_wod_session=active_wod_session,
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


class GetStudentWorkoutDay:
    def execute(self, *, student, session_id: int) -> StudentWorkoutDayResult | None:
        workout = (
            SessionWorkout.objects.select_related('session', 'session__coach')
            .prefetch_related('blocks__movements')
            .filter(session_id=session_id, status=SessionWorkoutStatus.PUBLISHED)
            .first()
        )
        if workout is None:
            return None

        block_cards = []
        for block in workout.blocks.all():
            movement_cards = []
            for movement in block.movements.all():
                load_context_label, recommended_load, recommendation_copy = build_student_recommendation_preview(
                    student=student,
                    movement=movement,
                )
                recommendation_label = (
                    f'{recommended_load} kg'
                    if recommended_load is not None and movement.load_type != WorkoutLoadType.FIXED_KG
                    else (f'{recommended_load} kg' if recommended_load is not None else 'Sem carga automatica')
                )
                movement_cards.append(
                    StudentWorkoutMovementCard(
                        movement_label=movement.movement_label,
                        prescription_label=build_student_prescription_label(movement=movement),
                        load_context_label=load_context_label,
                        recommendation_label=recommendation_label,
                        recommendation_copy=recommendation_copy,
                        notes=movement.notes,
                    )
                )
            block_cards.append(
                StudentWorkoutBlockCard(
                    title=block.title,
                    kind_label=block.get_kind_display(),
                    notes=block.notes,
                    movements=tuple(movement_cards),
                )
            )

        return StudentWorkoutDayResult(
            session_title=workout.session.title,
            session_scheduled_label=workout.session.scheduled_at.strftime('%d/%m %H:%M'),
            coach_name=workout.session.coach.get_full_name() if workout.session.coach else 'Equipe OctoBox',
            workout_title=workout.title or workout.session.title,
            coach_notes=workout.coach_notes,
            blocks=tuple(block_cards),
        )
