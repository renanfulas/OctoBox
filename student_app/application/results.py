from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StudentSessionCard:
    title: str
    scheduled_label: str
    coach_name: str
    attendance_status: str
    notes: str


@dataclass(frozen=True, slots=True)
class StudentDashboardResult:
    student_name: str
    box_root_slug: str
    next_sessions: tuple[StudentSessionCard, ...]
    membership_label: str


@dataclass(frozen=True, slots=True)
class WorkoutPrescriptionResult:
    exercise_label: str
    percentage_label: str
    one_rep_max_label: str
    raw_load_label: str
    rounded_load_label: str
    observation: str
