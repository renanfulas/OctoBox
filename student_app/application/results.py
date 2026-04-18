from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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


@dataclass(frozen=True, slots=True)
class StudentDashboardResult:
    student_name: str
    box_root_slug: str
    next_sessions: tuple[StudentSessionCard, ...]
    membership_label: str
    home_mode: str
    focal_session: StudentSessionCard | None
    active_wod_session: StudentSessionCard | None


@dataclass(frozen=True, slots=True)
class StudentWorkoutMovementCard:
    movement_label: str
    prescription_label: str
    load_context_label: str
    recommendation_label: str
    recommendation_copy: str
    notes: str


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


@dataclass(frozen=True, slots=True)
class WorkoutPrescriptionResult:
    exercise_label: str
    percentage_label: str
    one_rep_max_label: str
    raw_load_label: str
    rounded_load_label: str
    observation: str
