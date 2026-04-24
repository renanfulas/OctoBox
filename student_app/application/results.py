from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class StudentPrimaryAction:
    kind: str
    label: str
    url_name: str
    method: str = 'get'
    payload: dict | None = None


@dataclass(frozen=True, slots=True)
class StudentProgressDay:
    date: date
    is_complete: bool
    kind: str = ''
    day_label: str = ''
    date_label: str = ''
    is_today: bool = False


@dataclass(frozen=True, slots=True)
class StudentRmOfTheDay:
    exercise_slug: str
    exercise_label: str
    one_rep_max_kg: Decimal | None
    recommended_load_kg: Decimal | None
    percentage: Decimal | None
    delta_kg: Decimal | None = None


@dataclass(frozen=True, slots=True)
class StudentSessionCard:
    session_id: int
    title: str
    scheduled_label: str
    scheduled_at: datetime
    coach_name: str
    attendance_status: str
    attendance_code: str
    notes: str
    can_confirm_presence: bool
    can_cancel_attendance: bool = False


@dataclass(frozen=True, slots=True)
class StudentMonthDay:
    date: date | None
    date_label: str
    day_label: str
    is_today: bool
    sessions: tuple[StudentSessionCard, ...] = ()


@dataclass(frozen=True, slots=True)
class StudentDashboardResult:
    student_name: str
    box_root_slug: str
    next_sessions: tuple[StudentSessionCard, ...]
    membership_label: str
    home_mode: str
    focal_session: StudentSessionCard | None
    active_wod_session: StudentSessionCard | None
    primary_action: StudentPrimaryAction | None = None
    progress_days: tuple[StudentProgressDay, ...] = ()
    rm_of_the_day: StudentRmOfTheDay | None = None
    next_useful_context: str = ''


@dataclass(frozen=True, slots=True)
class StudentWorkoutMovementCard:
    movement_label: str
    prescription_label: str
    load_context_label: str
    recommendation_label: str
    recommendation_copy: str
    notes: str
    recommended_load_kg: Decimal | None = None
    base_rm_kg: Decimal | None = None
    percentage: Decimal | None = None
    is_primary_recommendation: bool = False


@dataclass(frozen=True, slots=True)
class StudentWorkoutBlockCard:
    title: str
    kind_label: str
    notes: str
    movements: tuple[StudentWorkoutMovementCard, ...]


@dataclass(frozen=True, slots=True)
class StudentWorkoutDayResult:
    session_title: str
    session_scheduled_label: str
    coach_name: str
    workout_title: str
    coach_notes: str
    blocks: tuple[StudentWorkoutBlockCard, ...]
    primary_recommendation: StudentWorkoutMovementCard | None = None


@dataclass(frozen=True, slots=True)
class WorkoutPrescriptionResult:
    exercise_label: str
    percentage_label: str
    one_rep_max_label: str
    raw_load_label: str
    rounded_load_label: str
    observation: str
