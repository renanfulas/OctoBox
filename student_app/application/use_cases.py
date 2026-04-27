from __future__ import annotations

from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal
import time as perf_time

from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession
from operations.session_snapshots import build_class_session_runtime_state
from student_app.application.agenda_snapshots import get_student_agenda_snapshot
from student_app.application.cache_telemetry import record_student_app_perf
from student_app.application.home_snapshots import build_student_progress_days, get_student_home_rm_snapshot, get_student_home_snapshot
from student_app.application.rm_snapshots import build_student_rm_record_map
from student_app.application.results import (
    StudentPrimaryAction,
    StudentDashboardResult,
    StudentMonthDay,
    StudentRmOfTheDay,
    StudentSessionCard,
    StudentWorkoutBlockCard,
    StudentWorkoutDayResult,
    StudentWorkoutMovementCard,
    WorkoutPrescriptionResult,
)
from student_app.domain.workout_prescription import build_workout_prescription
from student_app.application.wod_snapshots import get_published_student_workout_snapshot
from student_app.models import (
    SessionWorkout,
    SessionWorkoutStatus,
    WorkoutLoadType,
)
from student_app.application.timezone import localize_box_datetime, resolve_box_timezone
from student_app.brazilian_holidays import get_brazilian_holiday_name


WEEKDAY_LABELS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom')
FULL_WEEKDAY_LABELS = ('Segunda-feira', 'Terca-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sabado', 'Domingo')


def _movement_value(movement, field_name):
    if isinstance(movement, dict):
        return movement.get(field_name)
    return getattr(movement, field_name, None)


def _format_attendance_status(*, attendance):
    if attendance is None:
        return 'Sem reserva'
    status = attendance.status
    if status == AttendanceStatus.CHECKED_IN:
        return 'Presenca confirmada'
    if status == AttendanceStatus.CANCELED:
        return 'Reserva cancelada'
    if hasattr(attendance, 'get_status_display'):
        return attendance.get_status_display()
    return dict(AttendanceStatus.choices).get(status, status or 'Sem reserva')


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
            rm_record_map = build_student_rm_record_map(
                student=student,
                box_root_slug=getattr(getattr(student, 'app_identity', None), 'box_root_slug', None),
                request_perf=None,
            )
            rm_card = rm_record_map.get(movement_slug)
            exercise_max = rm_card.record if rm_card is not None else None
            return _build_student_recommendation_payload_from_rm(movement=movement, exercise_max=exercise_max)
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


def _build_student_recommendation_payload_from_rm(*, movement, exercise_max):
    load_type = _movement_value(movement, 'load_type')
    load_value = _movement_value(movement, 'load_value')
    if load_type == WorkoutLoadType.PERCENTAGE_OF_RM and load_value is not None:
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
    reservation_horizon_days = 1

    def _resolve_active_reserved_session(self, *, attendances, now, box_root_slug):
        active_codes = {
            AttendanceStatus.BOOKED,
            AttendanceStatus.CHECKED_IN,
            AttendanceStatus.CHECKED_OUT,
        }
        reserved_sessions = []
        for attendance in attendances:
            if attendance.status not in active_codes:
                continue
            scheduled_at = localize_box_datetime(attendance.session.scheduled_at, box_root_slug=box_root_slug)
            ends_at = scheduled_at + timedelta(minutes=attendance.session.duration_minutes or 60)
            if ends_at <= now:
                continue
            reserved_sessions.append((scheduled_at, attendance.session_id))
        if not reserved_sessions:
            return None
        reserved_sessions.sort(key=lambda item: item[0])
        return reserved_sessions[0][1]

    def _build_booking_block_reason(
        self,
        *,
        attendance,
        runtime_state,
        has_other_active_reservation,
        is_plan_blocked,
        is_within_booking_window,
    ):
        if is_plan_blocked:
            return 'Renove seu plano para reservar'
        if has_other_active_reservation:
            return 'Voce ja tem uma reserva ativa. Libere a proxima so depois que essa aula terminar.'
        if not is_within_booking_window:
            return 'Reserve apenas para hoje ou amanha.'
        if runtime_state['label'] != 'Agendada':
            return 'Reserva indisponivel para esta aula agora.'
        return ''

    def _build_session_capacity_snapshot(self, *, session, runtime_state):
        occupancy_statuses = {
            AttendanceStatus.BOOKED,
            AttendanceStatus.CHECKED_IN,
            AttendanceStatus.CHECKED_OUT,
        }
        occupied_slots = sum(
            1
            for attendance in session.attendances.all()
            if attendance.status in occupancy_statuses
        )
        capacity = session.capacity or 0
        available_slots = max(capacity - occupied_slots, 0)
        occupancy_ratio = (occupied_slots / capacity) if capacity else 0
        booking_closed = runtime_state['label'] in {'Em andamento', 'Finalizada'}

        if booking_closed:
            occupancy_percent = 100
            occupancy_label = 'Fechada'
            occupancy_fill_class = 'class-occupancy-closed'
            occupancy_note = (
                'Entradas encerradas enquanto a aula estiver em andamento.'
                if runtime_state['label'] == 'Em andamento'
                else 'Entradas encerradas porque a aula já foi finalizada.'
            )
        else:
            occupancy_percent = round(occupancy_ratio * 100)
            if occupancy_ratio >= 0.9:
                occupancy_fill_class = 'class-occupancy-critical'
            elif occupancy_ratio >= 0.7:
                occupancy_fill_class = 'class-occupancy-high'
            elif occupancy_ratio >= 0.5:
                occupancy_fill_class = 'class-occupancy-medium'
            else:
                occupancy_fill_class = 'class-occupancy-available'
            occupancy_label = 'Com vagas' if available_slots > 0 else 'Sem vagas'
            occupancy_note = f'{available_slots} vaga(s) restante(s)'

        return {
            'occupied_slots': occupied_slots,
            'available_slots': available_slots,
            'capacity': capacity,
            'occupancy_percent': occupancy_percent,
            'occupancy_label': occupancy_label,
            'occupancy_fill_class': occupancy_fill_class,
            'occupancy_note': occupancy_note,
            'booking_closed': booking_closed,
        }

    def _build_session_capacity_from_agenda_snapshot(self, *, session_snapshot, runtime_state):
        capacity = session_snapshot['capacity'] or 0
        occupied_slots = session_snapshot['occupied_slots'] or 0
        available_slots = max(capacity - occupied_slots, 0)
        occupancy_ratio = (occupied_slots / capacity) if capacity else 0
        booking_closed = runtime_state['label'] in {'Em andamento', 'Finalizada'}

        if booking_closed:
            return {
                'occupied_slots': occupied_slots,
                'available_slots': available_slots,
                'capacity': capacity,
                'occupancy_percent': 100,
                'occupancy_label': 'Fechada',
                'occupancy_fill_class': 'class-occupancy-closed',
                'occupancy_note': (
                    'Entradas encerradas enquanto a aula estiver em andamento.'
                    if runtime_state['label'] == 'Em andamento'
                    else 'Entradas encerradas porque a aula já foi finalizada.'
                ),
                'booking_closed': booking_closed,
            }

        if occupancy_ratio >= 0.9:
            occupancy_fill_class = 'class-occupancy-critical'
        elif occupancy_ratio >= 0.7:
            occupancy_fill_class = 'class-occupancy-high'
        elif occupancy_ratio >= 0.5:
            occupancy_fill_class = 'class-occupancy-medium'
        else:
            occupancy_fill_class = 'class-occupancy-available'
        return {
            'occupied_slots': occupied_slots,
            'available_slots': available_slots,
            'capacity': capacity,
            'occupancy_percent': round(occupancy_ratio * 100),
            'occupancy_label': 'Com vagas' if available_slots > 0 else 'Sem vagas',
            'occupancy_fill_class': occupancy_fill_class,
            'occupancy_note': f'{available_slots} vaga(s) restante(s)',
            'booking_closed': booking_closed,
        }

    def _build_runtime_state_from_agenda_snapshot(self, *, session_snapshot, scheduled_at, now):
        ends_at = scheduled_at + timedelta(minutes=session_snapshot['duration_minutes'] or 60)
        status = session_snapshot['status']
        if status == 'canceled':
            return {
                'label': 'Cancelada',
                'pill_class': 'class-status-canceled',
                'starts_at': scheduled_at,
                'ends_at': ends_at,
                'should_mark_completed': False,
            }
        if scheduled_at <= now <= ends_at:
            return {
                'label': 'Em andamento',
                'pill_class': 'class-status-in-progress',
                'starts_at': scheduled_at,
                'ends_at': ends_at,
                'should_mark_completed': False,
            }
        if now > ends_at:
            return {
                'label': 'Finalizada',
                'pill_class': 'class-status-completed',
                'starts_at': scheduled_at,
                'ends_at': ends_at,
                'should_mark_completed': status != 'completed',
            }
        if status == 'completed':
            return {
                'label': 'Finalizada',
                'pill_class': 'class-status-completed',
                'starts_at': scheduled_at,
                'ends_at': ends_at,
                'should_mark_completed': False,
            }
        return {
            'label': 'Agendada',
            'pill_class': 'class-status-scheduled',
            'starts_at': scheduled_at,
            'ends_at': ends_at,
            'should_mark_completed': False,
        }

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

    def _resolve_rm_of_the_day(self, *, student, session_card, box_root_slug):
        if session_card is None:
            return None
        workout_snapshot = get_published_student_workout_snapshot(
            session_id=session_card.session_id,
            box_root_slug=box_root_slug,
        )
        if workout_snapshot is None:
            return None
        rm_record_map = build_student_rm_record_map(student=student, box_root_slug=box_root_slug)
        for block in workout_snapshot['blocks']:
            for movement in block['movements']:
                if movement['load_type'] != WorkoutLoadType.PERCENTAGE_OF_RM or movement['load_value'] is None:
                    continue
                rm_card = rm_record_map.get(movement['movement_slug'])
                exercise_max = rm_card.record if rm_card is not None else None
                recommended_load = None
                delta_kg = None
                if exercise_max is not None:
                    prescription = build_workout_prescription(
                        one_rep_max_kg=exercise_max.one_rep_max_kg,
                        percentage=movement['load_value'],
                    )
                    recommended_load = prescription.rounded_load_kg
                    delta_kg = rm_card.delta_kg
                return StudentRmOfTheDay(
                    exercise_slug=movement['movement_slug'],
                    exercise_label=movement['movement_label'],
                    one_rep_max_kg=exercise_max.one_rep_max_kg if exercise_max is not None else None,
                    recommended_load_kg=recommended_load,
                    percentage=movement['load_value'],
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
                kind='book_session',
                label='Reservar',
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
        if focal_session is not None:
            if focal_session.is_plan_blocked:
                return StudentPrimaryAction(
                    kind='renew_plan',
                    label='Renove seu plano',
                    url_name='student-app-settings',
                    disabled=True,
                    help_text=focal_session.plan_block_reason,
                )
            if focal_session.can_book:
                return StudentPrimaryAction(
                    kind='book_session',
                    label='Reservar',
                    url_name='student-app-confirm-attendance',
                    method='post',
                    payload={'session_id': focal_session.session_id},
                    help_text=focal_session.booking_block_reason,
                )
        return StudentPrimaryAction(
            kind='open_grade',
            label='Abrir grade',
            url_name='student-app-grade',
        )

    def execute(self, *, identity, selected_date=None, window_days: int | None = None, request_perf=None) -> StudentDashboardResult:
        started_at = perf_time.perf_counter()
        box_timezone = resolve_box_timezone(box_root_slug=identity.box_root_slug)
        now = timezone.localtime(timezone.now(), box_timezone)
        today = now.date()
        if selected_date is None and not window_days:
            query_start_date = today
            agenda_snapshot = get_student_agenda_snapshot(
                box_root_slug=identity.box_root_slug,
                start_date=query_start_date,
                box_timezone=box_timezone,
                limit=12,
                request_perf=request_perf,
            )
        else:
            query_start_date = selected_date or today
            agenda_snapshot = get_student_agenda_snapshot(
                box_root_slug=identity.box_root_slug,
                start_date=query_start_date,
                box_timezone=box_timezone,
                window_days=window_days or 1,
                request_perf=request_perf,
            )
        session_snapshots = agenda_snapshot['sessions']
        session_ids = [session_snapshot['session_id'] for session_snapshot in session_snapshots]
        home_snapshot = get_student_home_snapshot(
            identity=identity,
            start_date=query_start_date,
            session_ids=session_ids,
            window_days=window_days,
            limit=(12 if selected_date is None and not window_days else None),
            now=now,
            progress_days_builder=build_student_progress_days,
            request_perf=request_perf,
        )
        attendance_by_session = home_snapshot['attendance_by_session']
        has_active_plan = home_snapshot['has_active_plan']
        active_reserved_session_id = home_snapshot['active_reserved_session_id']
        latest_canceled_session_id = home_snapshot.get('latest_canceled_session_id')
        booking_horizon_date = today + timedelta(days=self.reservation_horizon_days)
        session_cards = []
        for session_snapshot in session_snapshots:
            session_id = session_snapshot['session_id']
            attendance_status_code = attendance_by_session.get(session_id, '')
            is_canceled_attendance = attendance_status_code == AttendanceStatus.CANCELED
            scheduled_at = localize_box_datetime(
                datetime.fromisoformat(session_snapshot['scheduled_at']),
                box_root_slug=identity.box_root_slug,
            )
            runtime_state = self._build_runtime_state_from_agenda_snapshot(
                session_snapshot=session_snapshot,
                scheduled_at=scheduled_at,
                now=now,
            )
            capacity_snapshot = self._build_session_capacity_from_agenda_snapshot(
                session_snapshot=session_snapshot,
                runtime_state=runtime_state,
            )
            plan_block_reason = 'Renove seu plano para reservar'
            is_plan_blocked = not has_active_plan and not attendance_status_code
            is_within_booking_window = scheduled_at.date() <= booking_horizon_date
            has_other_active_reservation = (
                active_reserved_session_id is not None
                and active_reserved_session_id != session_id
                and attendance_status_code not in {
                    AttendanceStatus.BOOKED,
                    AttendanceStatus.CHECKED_IN,
                    AttendanceStatus.CHECKED_OUT,
                }
            )
            can_book = (
                not attendance_status_code
                and not has_other_active_reservation
                and not is_plan_blocked
                and is_within_booking_window
                and runtime_state['label'] == 'Agendada'
            )
            can_rebook = (
                is_canceled_attendance
                and latest_canceled_session_id == session_id
                and not has_other_active_reservation
                and not is_plan_blocked
                and is_within_booking_window
                and runtime_state['label'] == 'Agendada'
            )
            booking_block_reason = self._build_booking_block_reason(
                attendance=type('AttendanceState', (), {'status': attendance_status_code})() if attendance_status_code else None,
                runtime_state=runtime_state,
                has_other_active_reservation=has_other_active_reservation,
                is_plan_blocked=is_plan_blocked,
                is_within_booking_window=is_within_booking_window,
            )
            session_cards.append(
                StudentSessionCard(
                    session_id=session_id,
                    title=session_snapshot['title'],
                    scheduled_label=scheduled_at.strftime('%d/%m %H:%M'),
                    scheduled_at=scheduled_at,
                    coach_name=session_snapshot['coach_name'],
                    attendance_status=_format_attendance_status(
                        attendance=type('AttendanceState', (), {'status': attendance_status_code})() if attendance_status_code else None
                    ),
                    attendance_code=attendance_status_code,
                    notes=session_snapshot['notes'],
                    can_confirm_presence=can_book or can_rebook,
                    can_cancel_attendance=(
                        attendance_status_code == AttendanceStatus.BOOKED
                        and now <= scheduled_at - timedelta(hours=1)
                    ),
                    can_book=can_book,
                    is_day_blocked=has_other_active_reservation,
                    day_block_reason=booking_block_reason if has_other_active_reservation else '',
                    is_plan_blocked=is_plan_blocked,
                    plan_block_reason=plan_block_reason if is_plan_blocked else '',
                    runtime_status_label=runtime_state['label'],
                    runtime_status_pill_class=runtime_state['pill_class'],
                    is_starting_soon=scheduled_at > now and scheduled_at <= now + timedelta(minutes=30),
                    workout_titles=tuple(session_snapshot['workout_titles']),
                    booking_block_reason=booking_block_reason,
                    occupied_slots=capacity_snapshot['occupied_slots'],
                    available_slots=capacity_snapshot['available_slots'],
                    capacity=capacity_snapshot['capacity'],
                    occupancy_percent=capacity_snapshot['occupancy_percent'],
                    occupancy_label=capacity_snapshot['occupancy_label'],
                    occupancy_fill_class=capacity_snapshot['occupancy_fill_class'],
                    occupancy_note=capacity_snapshot['occupancy_note'],
                    booking_closed=capacity_snapshot['booking_closed'],
                    is_latest_canceled_session=(latest_canceled_session_id == session_id),
                )
            )
        next_sessions = tuple(session_cards)
        session_snapshot_by_id = {
            session_snapshot['session_id']: session_snapshot
            for session_snapshot in session_snapshots
        }
        home_mode, active_wod_session = self._resolve_home_mode(session_cards=next_sessions, now=now)
        membership_label = home_snapshot['membership_label']
        booked_future_session = next((session for session in next_sessions if session.session_id == active_reserved_session_id), None)
        focal_session = booked_future_session or (next_sessions[0] if next_sessions else None)
        rm_target_session = active_wod_session or focal_session
        rm_target_snapshot = session_snapshot_by_id.get(rm_target_session.session_id) if rm_target_session is not None else None
        rm_of_the_day = get_student_home_rm_snapshot(
            identity=identity,
            session_id=rm_target_session.session_id if rm_target_session is not None else None,
            movement_hint=(
                {
                    'movement_slug': rm_target_snapshot.get('rm_movement_slug', ''),
                    'movement_label': rm_target_snapshot.get('rm_movement_label', ''),
                    'load_value': rm_target_snapshot.get('rm_movement_load_value'),
                }
                if rm_target_snapshot and rm_target_snapshot.get('rm_movement_slug')
                else None
            ),
            request_perf=request_perf,
        )
        primary_action = self._resolve_primary_action(
            home_mode=home_mode,
            focal_session=focal_session,
            active_wod_session=active_wod_session,
            rm_of_the_day=rm_of_the_day,
        )
        next_useful_context = (
            'WOD ativo agora'
            if home_mode == 'wod_active'
            else ('Reserva ativa no radar' if booked_future_session else ('Proxima aula no radar' if focal_session else 'Sem aula publicada'))
        )
        result = StudentDashboardResult(
            student_name=identity.student.full_name,
            box_root_slug=identity.box_root_slug,
            next_sessions=next_sessions,
            membership_label=membership_label,
            home_mode=home_mode,
            focal_session=focal_session,
            active_wod_session=active_wod_session,
            primary_action=primary_action,
            progress_days=home_snapshot['progress_days'],
            rm_of_the_day=rm_of_the_day,
            next_useful_context=next_useful_context,
            available_session=next((session for session in next_sessions if session.can_book or session.is_plan_blocked), None),
        )
        record_student_app_perf(
            request_perf,
            'home',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=0,
            build_ms=0,
            cache_hit=False,
        )
        return result


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
    def execute(self, *, student, exercise_slug: str, percentage: Decimal, request_perf=None) -> WorkoutPrescriptionResult | None:
        rm_record_map = build_student_rm_record_map(
            student=student,
            box_root_slug=getattr(getattr(student, 'app_identity', None), 'box_root_slug', None),
            request_perf=request_perf,
        )
        rm_card = rm_record_map.get(exercise_slug)
        if rm_card is None:
            return None
        prescription = build_workout_prescription(
            one_rep_max_kg=rm_card.record.one_rep_max_kg,
            percentage=percentage,
        )
        return WorkoutPrescriptionResult(
            exercise_label=rm_card.record.exercise_label,
            percentage_label=f'{percentage}%',
            one_rep_max_label=f'{rm_card.record.one_rep_max_kg} kg',
            raw_load_label=f'{prescription.raw_load_kg} kg',
            rounded_load_label=f'{prescription.rounded_load_kg} kg',
            observation=prescription.observation,
        )


class GetStudentWorkoutDay:
    def execute(self, *, student, session_id: int, box_root_slug: str | None = None, request_perf=None) -> StudentWorkoutDayResult | None:
        started_at = perf_time.perf_counter()
        if box_root_slug is None:
            box_root_slug = getattr(getattr(student, 'app_identity', None), 'box_root_slug', None)
        workout_snapshot = get_published_student_workout_snapshot(
            session_id=session_id,
            box_root_slug=box_root_slug,
            request_perf=request_perf,
        )
        if workout_snapshot is None:
            return None

        percentage_slugs = {
            movement['movement_slug']
            for block in workout_snapshot['blocks']
            for movement in block['movements']
            if movement['load_type'] == WorkoutLoadType.PERCENTAGE_OF_RM and movement['load_value'] is not None
        }
        rm_record_map = build_student_rm_record_map(student=student, box_root_slug=box_root_slug, request_perf=request_perf)
        exercise_max_by_slug = {
            slug: rm_record_map[slug].record
            for slug in percentage_slugs
            if slug in rm_record_map
        } if percentage_slugs else {}

        block_cards = []
        primary_recommendation = None
        for block in workout_snapshot['blocks']:
            movement_cards = []
            for movement in block['movements']:
                recommendation_payload = _build_student_recommendation_payload_from_rm(
                    movement=movement,
                    exercise_max=exercise_max_by_slug.get(movement['movement_slug']),
                )
                load_context_label = recommendation_payload['load_context_label']
                recommended_load = recommendation_payload['recommended_load_kg']
                recommendation_copy = recommendation_payload['recommendation_copy']
                recommendation_label = (
                    f'{recommended_load} kg'
                    if recommended_load is not None and movement['load_type'] != WorkoutLoadType.FIXED_KG
                    else (f'{recommended_load} kg' if recommended_load is not None else 'Sem carga automatica')
                )
                movement_card = StudentWorkoutMovementCard(
                    movement_label=movement['movement_label'],
                    prescription_label=build_student_prescription_label(movement=movement),
                    load_context_label=load_context_label,
                    recommendation_label=recommendation_label,
                    recommendation_copy=recommendation_copy,
                    notes=movement['notes'],
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
                    title=block['title'],
                    kind_label=block['kind_label'],
                    notes=block['notes'],
                    movements=tuple(movement_cards),
                )
            )

        scheduled_at = localize_box_datetime(
            datetime.fromisoformat(workout_snapshot['session_scheduled_at']),
            box_root_slug=box_root_slug,
        )
        result = StudentWorkoutDayResult(
            session_title=workout_snapshot['session_title'],
            session_scheduled_label=scheduled_at.strftime('%d/%m %H:%M'),
            session_weekday_label=FULL_WEEKDAY_LABELS[scheduled_at.weekday()],
            coach_name=workout_snapshot['coach_name'],
            workout_title=workout_snapshot['workout_title'],
            coach_notes=workout_snapshot['coach_notes'],
            blocks=tuple(block_cards),
            primary_recommendation=primary_recommendation,
        )
        record_student_app_perf(
            request_perf,
            'wod',
            total_ms=(perf_time.perf_counter() - started_at) * 1000,
            cache_lookup_ms=0,
            build_ms=0,
            cache_hit=False,
        )
        return result
