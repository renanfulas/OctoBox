from __future__ import annotations

from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession
from operations.session_snapshots import build_class_session_runtime_state
from student_app.application.results import (
    StudentPrimaryAction,
    StudentDashboardResult,
    StudentMonthDay,
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
from student_app.application.timezone import localize_box_datetime, resolve_box_timezone
from student_app.brazilian_holidays import get_brazilian_holiday_name


WEEKDAY_LABELS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom')


def _movement_value(movement, field_name):
    if isinstance(movement, dict):
        return movement.get(field_name)
    return getattr(movement, field_name, None)


def _format_attendance_status(*, attendance):
    if attendance is None:
        return 'Sem reserva'
    if attendance.status == AttendanceStatus.CHECKED_IN:
        return 'Presenca confirmada'
    return attendance.get_status_display()


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

    def _resolve_day_block_map(self, *, attendances):
        day_blocks = {}
        for attendance in attendances:
            session_date = attendance.session.scheduled_at.date()
            if attendance.status == AttendanceStatus.CHECKED_IN:
                day_blocks[session_date] = 'Presenca confirmada'
            elif attendance.status == AttendanceStatus.BOOKED and session_date not in day_blocks:
                day_blocks[session_date] = 'Voce ja tem uma aula reservada hoje'
        return day_blocks

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
        days = [today + timedelta(days=offset) for offset in range(7)]
        activities = (
            StudentAppActivity.objects
            .filter(student=student, activity_date__in=days)
            .order_by('activity_date', 'created_at')
        )
        activity_by_day = {}
        for activity in activities:
            activity_by_day.setdefault(activity.activity_date, activity.kind)
        return tuple(
            StudentProgressDay(
                date=day,
                is_complete=day in activity_by_day,
                kind=activity_by_day.get(day, ''),
                day_label='Hoje' if day == today else WEEKDAY_LABELS[day.weekday()],
                date_label=day.strftime('%d/%m'),
                is_today=day == today,
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
                    history = (
                        StudentExerciseMaxHistory.objects
                        .filter(student=student, exercise_slug=movement.movement_slug)
                        .order_by('-created_at', '-id')
                        .first()
                    )
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

    def _resolve_primary_action(self, *, home_mode, focal_session, active_wod_session, rm_of_the_day, available_session):
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
        if focal_session is not None and focal_session.attendance_code in {
            AttendanceStatus.BOOKED,
            AttendanceStatus.CHECKED_IN,
            AttendanceStatus.CHECKED_OUT,
        }:
            return StudentPrimaryAction(
                kind='open_grade',
                label='Abrir grade',
                url_name='student-app-grade',
            )
        if available_session is not None:
            if available_session.is_plan_blocked:
                return StudentPrimaryAction(
                    kind='renew_plan',
                    label='Renove seu plano',
                    url_name='student-app-settings',
                    disabled=True,
                    help_text=available_session.plan_block_reason,
                )
            if available_session.can_book:
                return StudentPrimaryAction(
                    kind='book_session',
                    label='Reservar',
                    url_name='student-app-confirm-attendance',
                    method='post',
                    payload={'session_id': available_session.session_id},
                )
        return StudentPrimaryAction(
            kind='open_grade',
            label='Abrir grade',
            url_name='student-app-grade',
        )

    def execute(self, *, identity) -> StudentDashboardResult:
        box_timezone = resolve_box_timezone(box_root_slug=identity.box_root_slug)
        now = timezone.localtime(timezone.now(), box_timezone)
        today = now.date()
        sessions = (
            ClassSession.objects.filter(
                status__in=['scheduled', 'open'],
                scheduled_at__gte=timezone.make_aware(datetime.combine(today, time.min), box_timezone),
            )
            .order_by('scheduled_at')
            .prefetch_related('attendances', 'coach')[:12]
        )
        attendance_queryset = Attendance.objects.filter(student=identity.student, session__in=sessions).select_related('session')
        attendance_by_session = {
            attendance.session_id: attendance
            for attendance in attendance_queryset
        }
        day_block_map = self._resolve_day_block_map(attendances=attendance_queryset)
        workout_title_map = {}
        for workout in SessionWorkout.objects.filter(session__in=sessions, status=SessionWorkoutStatus.PUBLISHED).select_related('session'):
            workout_title_map.setdefault(workout.session_id, []).append(workout.title)
        enrollment = (
            Enrollment.objects.select_related('plan')
            .filter(student=identity.student, status=EnrollmentStatus.ACTIVE)
            .order_by('-created_at')
            .first()
        )
        latest_enrollment = (
            Enrollment.objects.select_related('plan')
            .filter(student=identity.student)
            .order_by('-created_at')
            .first()
        )
        has_active_plan = enrollment is not None or latest_enrollment is None
        session_cards = []
        for session in sessions:
            attendance = attendance_by_session.get(session.id)
            scheduled_at = localize_box_datetime(session.scheduled_at, box_root_slug=identity.box_root_slug)
            runtime_state = build_class_session_runtime_state(session, now=now)
            is_day_blocked = session.scheduled_at.date() in day_block_map and attendance is None
            plan_block_reason = 'Renove seu plano para reservar'
            is_plan_blocked = not has_active_plan and attendance is None
            can_book = (
                attendance is None
                and not is_day_blocked
                and not is_plan_blocked
                and runtime_state['label'] == 'Agendada'
            )
            session_cards.append(
                StudentSessionCard(
                    session_id=session.id,
                    title=session.title,
                    scheduled_label=scheduled_at.strftime('%d/%m %H:%M'),
                    scheduled_at=scheduled_at,
                    coach_name=session.coach.get_full_name() if session.coach else 'Equipe OctoBox',
                    attendance_status=_format_attendance_status(attendance=attendance),
                    attendance_code=(attendance.status if attendance else ''),
                    notes=session.notes,
                    can_confirm_presence=(
                        attendance is None
                        or attendance.status in {
                            AttendanceStatus.ABSENT,
                            AttendanceStatus.CANCELED,
                        }
                    ),
                    can_cancel_attendance=(
                        attendance is not None
                        and attendance.status == AttendanceStatus.BOOKED
                        and now <= scheduled_at - timedelta(hours=1)
                    ),
                    can_book=can_book,
                    is_day_blocked=is_day_blocked,
                    day_block_reason=day_block_map.get(session.scheduled_at.date(), ''),
                    is_plan_blocked=is_plan_blocked,
                    plan_block_reason=plan_block_reason if is_plan_blocked else '',
                    runtime_status_label=runtime_state['label'],
                    runtime_status_pill_class=runtime_state['pill_class'],
                    is_starting_soon=scheduled_at > now and scheduled_at <= now + timedelta(minutes=30),
                    workout_titles=tuple(workout_title_map.get(session.id, ())),
                )
            )
        next_sessions = tuple(session_cards)
        home_mode, active_wod_session = self._resolve_home_mode(session_cards=next_sessions, now=now)
        membership_label = enrollment.plan.name if enrollment and enrollment.plan_id else 'Sem plano ativo'
        booked_future_session = next(
            (
                session for session in next_sessions
                if session.attendance_code in {AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT}
                and session.scheduled_at >= now
            ),
            None,
        )
        available_session = next((session for session in next_sessions if session.can_book or session.is_plan_blocked), None)
        rm_of_the_day = self._resolve_rm_of_the_day(
            student=identity.student,
            session_card=active_wod_session or booked_future_session or available_session or (next_sessions[0] if next_sessions else None),
        )
        primary_action = self._resolve_primary_action(
            home_mode=home_mode,
            focal_session=booked_future_session,
            active_wod_session=active_wod_session,
            rm_of_the_day=rm_of_the_day,
            available_session=available_session,
        )
        next_useful_context = (
            'WOD ativo agora'
            if home_mode == 'wod_active'
            else ('Proxima aula no radar' if booked_future_session or available_session else 'Sem aula publicada')
        )
        return StudentDashboardResult(
            student_name=identity.student.full_name,
            box_root_slug=identity.box_root_slug,
            next_sessions=next_sessions,
            membership_label=membership_label,
            home_mode=home_mode,
            focal_session=booked_future_session or available_session,
            active_wod_session=active_wod_session,
            primary_action=primary_action,
            progress_days=self._build_progress_days(student=identity.student, now=now),
            rm_of_the_day=rm_of_the_day,
            next_useful_context=next_useful_context,
            available_session=available_session,
        )


class GetStudentMonthSchedule:
    def execute(self, *, identity, reference_date=None) -> tuple[StudentMonthDay, ...]:
        box_timezone = resolve_box_timezone(box_root_slug=identity.box_root_slug)
        today = timezone.localtime(timezone.now(), box_timezone).date()
        reference_date = reference_date or today
        month_start = reference_date.replace(day=1)
        _, last_day = monthrange(reference_date.year, reference_date.month)
        month_end = reference_date.replace(day=last_day)
        start_at = timezone.make_aware(datetime.combine(month_start, time.min), box_timezone)
        end_at = timezone.make_aware(datetime.combine(month_end, time.max), box_timezone)
        sessions = (
            ClassSession.objects.filter(
                status__in=['scheduled', 'open'],
                scheduled_at__gte=start_at,
                scheduled_at__lte=end_at,
            )
            .order_by('scheduled_at')
            .prefetch_related('attendances', 'coach')
        )
        attendance_by_session = {
            attendance.session_id: attendance
            for attendance in Attendance.objects.filter(student=identity.student, session__in=sessions).select_related('session')
        }
        workout_title_map = {}
        for workout in SessionWorkout.objects.filter(session__in=sessions, status=SessionWorkoutStatus.PUBLISHED).select_related('session'):
            workout_title_map.setdefault(workout.session_id, []).append(workout.title)
        now = timezone.localtime(timezone.now(), box_timezone)
        sessions_by_date = {}
        for session in sessions:
            attendance = attendance_by_session.get(session.id)
            scheduled_at = localize_box_datetime(session.scheduled_at, box_root_slug=identity.box_root_slug)
            runtime_state = build_class_session_runtime_state(session, now=now)
            card = StudentSessionCard(
                session_id=session.id,
                title=session.title,
                scheduled_label=scheduled_at.strftime('%d/%m %H:%M'),
                scheduled_at=scheduled_at,
                coach_name=session.coach.get_full_name() if session.coach else 'Equipe OctoBox',
                attendance_status=_format_attendance_status(attendance=attendance),
                attendance_code=(attendance.status if attendance else ''),
                notes=session.notes,
                can_confirm_presence=(
                    attendance is None
                    or attendance.status in {
                        AttendanceStatus.ABSENT,
                        AttendanceStatus.CANCELED,
                    }
                ),
                can_cancel_attendance=(
                    attendance is not None
                    and attendance.status == AttendanceStatus.BOOKED
                    and now <= scheduled_at - timedelta(hours=1)
                ),
                can_book=attendance is None and runtime_state['label'] == 'Agendada',
                runtime_status_label=runtime_state['label'],
                runtime_status_pill_class=runtime_state['pill_class'],
                is_starting_soon=scheduled_at > now and scheduled_at <= now + timedelta(minutes=30),
                workout_titles=tuple(workout_title_map.get(session.id, ())),
            )
            sessions_by_date.setdefault(scheduled_at.date(), []).append(card)

        days = []
        for _ in range(month_start.weekday()):
            days.append(StudentMonthDay(date=None, date_label='', day_label='', is_today=False, preview_state='blank'))
        for day_number in range(1, last_day + 1):
            day = reference_date.replace(day=day_number)
            holiday_name = get_brazilian_holiday_name(day)
            day_sessions = tuple(sessions_by_date.get(day, ()))
            attendance_labels = []
            for session in day_sessions:
                if session.attendance_code == AttendanceStatus.CHECKED_IN:
                    attendance_labels.append(f'{session.title} · Presenca confirmada')
                elif session.attendance_code == AttendanceStatus.BOOKED:
                    attendance_labels.append(f'{session.title} · Reservado')
            if attendance_labels:
                student_checkin_label = ' | '.join(attendance_labels)
            elif day < today:
                student_checkin_label = 'Sem presenca'
            else:
                student_checkin_label = 'Nenhum check-in'
            days.append(
                StudentMonthDay(
                    date=day,
                    date_label=str(day.day),
                    day_label=WEEKDAY_LABELS[day.weekday()],
                    is_today=day == today,
                    sessions=day_sessions,
                    holiday_name=holiday_name or '',
                    is_holiday=bool(holiday_name),
                    student_checkin_label=student_checkin_label,
                    preview_state='ready',
                )
            )
        return tuple(days)


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

        scheduled_at = localize_box_datetime(workout.session.scheduled_at)
        return StudentWorkoutDayResult(
            session_title=workout.session.title,
            session_scheduled_label=scheduled_at.strftime('%d/%m %H:%M'),
            coach_name=workout.session.coach.get_full_name() if workout.session.coach else 'Equipe OctoBox',
            workout_title=workout.title or workout.session.title,
            coach_notes=workout.coach_notes,
            blocks=tuple(block_cards),
            primary_recommendation=primary_recommendation,
        )
