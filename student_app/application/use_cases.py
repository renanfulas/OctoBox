from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.application.results import (
    StudentPrimaryAction,
    StudentDashboardResult,
    StudentProgressDay,
    StudentRmOfTheDay,
    StudentSessionCard,
    StudentWorkoutBlockCard,
    StudentWorkoutDayResult,
    StudentWorkoutMovementCard,
    WorkoutPrescriptionResult,
)
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.models import (
    SessionWorkout,
    SessionWorkoutStatus,
    StudentAppActivity,
    StudentExerciseMax,
    StudentExerciseMaxHistory,
    WorkoutLoadType,
)


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


def build_student_recommendation_payload(*, movement, student=None):
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
                return {
                    'load_context_label': 'Percentual do RM',
                    'recommended_load_kg': prescription.rounded_load_kg,
                    'recommendation_copy': f'Baseado no seu RM atual de {exercise_max.one_rep_max_kg} kg.',
                    'base_rm_kg': exercise_max.one_rep_max_kg,
                    'percentage': load_value,
                }
            return {
                'load_context_label': 'Percentual do RM',
                'recommended_load_kg': None,
                'recommendation_copy': 'Registre seu RM deste movimento para receber a carga recomendada aqui.',
                'base_rm_kg': None,
                'percentage': load_value,
            }
        return {
            'load_context_label': 'Percentual do RM',
            'recommended_load_kg': None,
            'recommendation_copy': 'O aluno vera a carga recomendada aqui quando tiver RM registrado para este movimento.',
            'base_rm_kg': None,
            'percentage': load_value,
        }
    if load_type == WorkoutLoadType.FIXED_KG and load_value is not None:
        return {
            'load_context_label': 'Carga fixa',
            'recommended_load_kg': load_value,
            'recommendation_copy': 'Esse bloco ja chega ao aluno com uma carga fechada definida pelo coach.',
            'base_rm_kg': None,
            'percentage': None,
        }
    return {
        'load_context_label': 'Carga livre',
        'recommended_load_kg': None,
        'recommendation_copy': 'O aluno vera a orientacao de ajuste livre com base na leitura de esforco e do coach.',
        'base_rm_kg': None,
        'percentage': None,
    }


def build_student_recommendation_preview(*, movement, student=None):
    payload = build_student_recommendation_payload(movement=movement, student=student)
    return (
        payload['load_context_label'],
        payload['recommended_load_kg'],
        payload['recommendation_copy'],
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

    def _build_progress_days(self, *, student, now):
        today = now.date()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        try:
            activities = (
                StudentAppActivity.objects
                .filter(student=student, activity_date__in=days)
                .order_by('activity_date', 'created_at')
            )
        except (OperationalError, ProgrammingError):
            activities = ()
        activity_by_day = {}
        for activity in activities:
            activity_by_day.setdefault(activity.activity_date, activity.kind)
        return tuple(
            StudentProgressDay(
                date=day,
                is_complete=day in activity_by_day,
                kind=activity_by_day.get(day, ''),
            )
            for day in days
        )

    def _resolve_rm_of_the_day(self, *, student, session_card):
        if session_card is None:
            return None
        workout = (
            SessionWorkout.objects
            .prefetch_related('blocks__movements')
            .filter(session_id=session_card.session_id, status=SessionWorkoutStatus.PUBLISHED)
            .first()
        )
        if workout is None:
            return None
        for block in workout.blocks.all():
            for movement in block.movements.all():
                if movement.load_type != WorkoutLoadType.PERCENTAGE_OF_RM or movement.load_value is None:
                    continue
                exercise_max = (
                    StudentExerciseMax.objects
                    .filter(student=student, exercise_slug=movement.movement_slug)
                    .order_by('-updated_at')
                    .first()
                )
                recommended_load = None
                delta_kg = None
                if exercise_max is not None:
                    prescription = build_workout_prescription(
                        one_rep_max_kg=exercise_max.one_rep_max_kg,
                        percentage=movement.load_value,
                    )
                    recommended_load = prescription.rounded_load_kg
                    try:
                        history = (
                            StudentExerciseMaxHistory.objects
                            .filter(student=student, exercise_slug=movement.movement_slug)
                            .order_by('-created_at', '-id')
                            .first()
                        )
                    except (OperationalError, ProgrammingError):
                        history = None
                    delta_kg = history.delta_kg if history is not None else None
                return StudentRmOfTheDay(
                    exercise_slug=movement.movement_slug,
                    exercise_label=movement.movement_label,
                    one_rep_max_kg=exercise_max.one_rep_max_kg if exercise_max is not None else None,
                    recommended_load_kg=recommended_load,
                    percentage=movement.load_value,
                    delta_kg=delta_kg,
                )
        return None

    def _resolve_primary_action(self, *, home_mode, focal_session, active_wod_session, rm_of_the_day):
        if home_mode == 'wod_active' and active_wod_session is not None:
            return StudentPrimaryAction(
                kind='open_wod',
                label='Abrir WOD',
                url_name='student-app-wod',
            )
        if focal_session is not None and focal_session.can_confirm_presence:
            return StudentPrimaryAction(
                kind='confirm_attendance',
                label='Confirmar presenca',
                url_name='student-app-confirm-attendance',
                method='post',
                payload={'session_id': focal_session.session_id},
            )
        if rm_of_the_day is not None and rm_of_the_day.one_rep_max_kg is None:
            return StudentPrimaryAction(
                kind='register_rm',
                label='Registrar RM',
                url_name='student-app-rm',
            )
        return StudentPrimaryAction(
            kind='open_grade',
            label='Abrir grade',
            url_name='student-app-grade',
        )

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
        rm_of_the_day = self._resolve_rm_of_the_day(
            student=identity.student,
            session_card=active_wod_session or (next_sessions[0] if next_sessions else None),
        )
        primary_action = self._resolve_primary_action(
            home_mode=home_mode,
            focal_session=next_sessions[0] if next_sessions else None,
            active_wod_session=active_wod_session,
            rm_of_the_day=rm_of_the_day,
        )
        next_useful_context = (
            'WOD ativo agora'
            if home_mode == 'wod_active'
            else ('Proxima aula no radar' if next_sessions else 'Sem aula publicada')
        )
        return StudentDashboardResult(
            student_name=identity.student.full_name,
            box_root_slug=identity.box_root_slug,
            next_sessions=next_sessions,
            membership_label=membership_label,
            home_mode=home_mode,
            focal_session=next_sessions[0] if next_sessions else None,
            active_wod_session=active_wod_session,
            primary_action=primary_action,
            progress_days=self._build_progress_days(student=identity.student, now=now),
            rm_of_the_day=rm_of_the_day,
            next_useful_context=next_useful_context,
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
        primary_recommendation = None
        for block in workout.blocks.all():
            movement_cards = []
            for movement in block.movements.all():
                recommendation_payload = build_student_recommendation_payload(
                    student=student,
                    movement=movement,
                )
                load_context_label = recommendation_payload['load_context_label']
                recommended_load = recommendation_payload['recommended_load_kg']
                recommendation_copy = recommendation_payload['recommendation_copy']
                recommendation_label = (
                    f'{recommended_load} kg'
                    if recommended_load is not None and movement.load_type != WorkoutLoadType.FIXED_KG
                    else (f'{recommended_load} kg' if recommended_load is not None else 'Sem carga automatica')
                )
                movement_card = StudentWorkoutMovementCard(
                    movement_label=movement.movement_label,
                    prescription_label=build_student_prescription_label(movement=movement),
                    load_context_label=load_context_label,
                    recommendation_label=recommendation_label,
                    recommendation_copy=recommendation_copy,
                    notes=movement.notes,
                    recommended_load_kg=recommended_load,
                    base_rm_kg=recommendation_payload['base_rm_kg'],
                    percentage=recommendation_payload['percentage'],
                    is_primary_recommendation=primary_recommendation is None and recommended_load is not None,
                )
                if movement_card.is_primary_recommendation:
                    primary_recommendation = movement_card
                movement_cards.append(movement_card)
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
            primary_recommendation=primary_recommendation,
        )
