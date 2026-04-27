"""
ARQUIVO: builders puros do planner semanal de WOD.

POR QUE ELE EXISTE:
- cria um contrato de leitura para a grade semanal sem depender de request, redirect ou messages.

O QUE ESTE ARQUIVO FAZ:
1. transforma sessoes de aula em celulas de planner.
2. define estado visual do WOD por celula.
3. agrupa celulas por dia da semana.

PONTOS CRITICOS:
- builder nao executa mutacao.
- builder nao conhece HTTP.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal

from django.urls import reverse
from django.utils import timezone

from operations.models import ClassSession, SessionStatus
from student_app.models import SessionWorkoutStatus

from .workout_support import build_policy_badge_from_snapshot, build_workout_review_snapshot, extract_latest_policy_snapshot


PlannerCellState = Literal['empty', 'draft', 'pending', 'published', 'sensitive']


@dataclass(frozen=True, slots=True)
class PlannerCellAction:
    key: str
    label: str
    href: str
    tone: str


@dataclass(frozen=True, slots=True)
class PlannerCell:
    session_id: int
    scheduled_at: datetime
    slot_label: str
    coach_label: str
    workout_id: int | None
    state: PlannerCellState
    is_sensitive: bool
    is_sensitive_diff: bool
    available_actions: tuple[str, ...]
    actions: tuple[PlannerCellAction, ...]
    can_duplicate_previous: bool
    duplicate_previous_url: str
    duplicate_previous_label: str
    href_editor: str
    href_preview: str
    session_title: str
    workout_title: str
    status_label: str
    summary: str
    primary_action_label: str
    primary_action_href: str
    secondary_action_label: str
    secondary_action_href: str
    policy_label: str
    trusted_template_label: str
    trusted_template_url: str
    trusted_template_picker_enabled: bool


@dataclass(frozen=True, slots=True)
class PlannerDay:
    date: date
    label: str
    weekday_label: str
    cells: tuple[PlannerCell, ...]


@dataclass(frozen=True, slots=True)
class PlannerWeek:
    week_start: date
    week_end: date
    label: str
    days: tuple[PlannerDay, ...]
    total_sessions: int
    empty_count: int
    draft_count: int
    pending_count: int
    published_count: int
    sensitive_count: int
    initial_focus_session_id: int | None


def resolve_week_start(value=None):
    if value:
        try:
            selected = date.fromisoformat(str(value))
        except ValueError:
            selected = timezone.localdate()
    else:
        selected = timezone.localdate()
    return selected - timedelta(days=selected.weekday())


def build_planner_week(*, week_start, sessions, previous_slot_source_map=None, current_role_slug='', trusted_template_options=()):
    days = []
    cells_by_date = {week_start + timedelta(days=offset): [] for offset in range(7)}
    ordered_cells = []
    counters = {
        'empty': 0,
        'draft': 0,
        'pending': 0,
        'published': 0,
        'sensitive': 0,
    }

    for session in sessions:
        cell = build_planner_cell(
            session=session,
            previous_slot_source=(
                (previous_slot_source_map or {}).get(session.id)
                if previous_slot_source_map is not None
                else None
            ),
            current_role_slug=current_role_slug,
            trusted_template_options=trusted_template_options,
        )
        cells_by_date[timezone.localtime(session.scheduled_at).date()].append(cell)
        ordered_cells.append(cell)
        counters[cell.state] += 1

    for offset in range(7):
        current_date = week_start + timedelta(days=offset)
        days.append(
            PlannerDay(
                date=current_date,
                label=current_date.strftime('%d/%m'),
                weekday_label=_weekday_label(current_date),
                cells=tuple(cells_by_date[current_date]),
            )
        )

    week_end = week_start + timedelta(days=6)
    initial_focus_cell = _resolve_initial_focus_cell(ordered_cells)
    return PlannerWeek(
        week_start=week_start,
        week_end=week_end,
        label=f'{week_start:%d/%m} - {week_end:%d/%m}',
        days=tuple(days),
        total_sessions=sum(len(day.cells) for day in days),
        empty_count=counters['empty'],
        draft_count=counters['draft'],
        pending_count=counters['pending'],
        published_count=counters['published'],
        sensitive_count=counters['sensitive'],
        initial_focus_session_id=initial_focus_cell.session_id if initial_focus_cell is not None else None,
    )


def build_planner_cell(*, session, previous_slot_source=None, current_role_slug='', trusted_template_options=()):
    workout = getattr(session, 'workout', None)
    is_sensitive = False
    is_sensitive_diff = False
    policy_badge = None
    has_trusted_template_picker = bool(trusted_template_options)
    if workout is None:
        state = 'empty'
        workout_title = 'Sem WOD'
        status_label = 'Sem WOD'
        summary = 'Aula pronta para receber um treino novo.'
        actions = ('create',)
        cell_actions = [
            PlannerCellAction(
                key='create',
                label='Criar WOD',
                href=reverse('coach-session-workout-editor', args=[session.id]),
                tone='primary',
            ),
        ]
        if current_role_slug in {'Owner', 'Manager'} and has_trusted_template_picker:
            cell_actions.append(
                PlannerCellAction(
                    key='open-template-picker',
                    label='Escolher template',
                    href='#wod-planner-template-picker',
                    tone='secondary',
                )
            )
        cell_actions = tuple(cell_actions)
    else:
        workout_title = workout.title or session.title
        review_snapshot = None
        if workout.status == SessionWorkoutStatus.PUBLISHED:
            policy_badge = build_policy_badge_from_snapshot(
                extract_latest_policy_snapshot(workout, preferred_event='published')
            )
            state = 'published'
            status_label = 'Publicado'
            summary = 'Treino publicado. Abra o editor ou consulte o historico recortado desta aula.' + (f' {policy_badge["label"]}.' if policy_badge else '')
            actions = ('open',)
            cell_actions = (
                PlannerCellAction(
                    key='open',
                    label='Abrir editor',
                    href=reverse('coach-session-workout-editor', args=[session.id]),
                    tone='primary',
                ),
                PlannerCellAction(
                    key='history',
                    label='Histórico',
                    href=f"{reverse('workout-publication-history')}?session_id={session.id}",
                    tone='secondary',
                ),
            )
        elif workout.status == SessionWorkoutStatus.PENDING_APPROVAL:
            review_snapshot = build_workout_review_snapshot(workout)
            policy_badge = build_policy_badge_from_snapshot(
                extract_latest_policy_snapshot(workout, preferred_event='submitted')
            )
            is_sensitive_diff = bool(review_snapshot['diff_snapshot']['is_sensitive'])
            is_sensitive = is_sensitive_diff
            state = 'sensitive' if is_sensitive else 'pending'
            status_label = 'Mudança sensível' if is_sensitive else 'Aguardando aprovação'
            summary = review_snapshot['review_summary'] + (f' {policy_badge["label"]}.' if policy_badge else '')
            actions = ('review',)
            cell_actions = (
                PlannerCellAction(
                    key='review',
                    label='Revisar fila',
                    href=f"{reverse('workout-approval-board')}?session_id={session.id}",
                    tone='primary',
                ),
                PlannerCellAction(
                    key='edit',
                    label='Abrir editor',
                    href=reverse('coach-session-workout-editor', args=[session.id]),
                    tone='secondary',
                ),
            )
        else:
            state = 'draft'
            status_label = workout.get_status_display()
            summary = 'Rascunho em progresso. Abra o editor para completar blocos e movimentos.'
            actions = ('edit',)
            cell_actions = (
                PlannerCellAction(
                    key='edit',
                    label='Abrir editor',
                    href=reverse('coach-session-workout-editor', args=[session.id]),
                    tone='primary',
                ),
            )

    return PlannerCell(
        session_id=session.id,
        scheduled_at=session.scheduled_at,
        slot_label=timezone.localtime(session.scheduled_at).strftime('%H:%M'),
        coach_label=_coach_label(session),
        workout_id=workout.id if workout is not None else None,
        state=state,
        is_sensitive=is_sensitive,
        is_sensitive_diff=is_sensitive_diff,
        available_actions=actions,
        actions=cell_actions,
        can_duplicate_previous=(workout is None and previous_slot_source is not None),
        duplicate_previous_url=reverse('workout-planner-duplicate-previous-slot', args=[session.id]),
        duplicate_previous_label=(
            f"Duplicar {previous_slot_source.title}" if previous_slot_source is not None else ''
        ),
        href_editor=reverse('coach-session-workout-editor', args=[session.id]),
        href_preview=reverse('coach-session-workout-editor', args=[session.id]),
        session_title=session.title,
        workout_title=workout_title,
        status_label=status_label,
        summary=summary,
        primary_action_label=cell_actions[0].label if cell_actions else '',
        primary_action_href=cell_actions[0].href if cell_actions else '',
        secondary_action_label=cell_actions[1].label if len(cell_actions) > 1 else '',
        secondary_action_href=cell_actions[1].href if len(cell_actions) > 1 else '',
        policy_label=policy_badge['label'] if workout is not None and policy_badge else '',
        trusted_template_label=('Escolher template' if workout is None and current_role_slug in {'Owner', 'Manager'} and has_trusted_template_picker else ''),
        trusted_template_url='',
        trusted_template_picker_enabled=(workout is None and current_role_slug in {'Owner', 'Manager'} and has_trusted_template_picker),
    )


def load_planner_sessions(*, week_start, current_role_slug, actor):
    week_start_at = timezone.make_aware(datetime.combine(week_start, time.min))
    week_end_at = week_start_at + timedelta(days=7)
    queryset = (
        ClassSession.objects.select_related('coach', 'workout')
        .prefetch_related('workout__blocks__movements', 'workout__revisions')
        .filter(status__in=(SessionStatus.SCHEDULED, SessionStatus.OPEN, SessionStatus.COMPLETED))
        .filter(scheduled_at__gte=week_start_at, scheduled_at__lt=week_end_at)
        .order_by('scheduled_at', 'id')
    )
    if current_role_slug == 'Coach':
        queryset = queryset.filter(coach=actor)
    return list(queryset)


def _coach_label(session):
    if session.coach is None:
        return 'Sem coach'
    return session.coach.get_full_name() or session.coach.username


def _weekday_label(value):
    labels = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom')
    return labels[value.weekday()]


def _resolve_initial_focus_cell(cells):
    if not cells:
        return None
    priority_order = {
        'sensitive': 0,
        'pending': 1,
        'draft': 2,
        'published': 3,
        'empty': 4,
    }
    return min(
        cells,
        key=lambda cell: (
            priority_order.get(cell.state, 99),
            timezone.localtime(cell.scheduled_at),
            cell.session_id,
        ),
    )


__all__ = [
    'PlannerCell',
    'PlannerCellAction',
    'PlannerDay',
    'PlannerWeek',
    'build_planner_cell',
    'build_planner_week',
    'load_planner_sessions',
    'resolve_week_start',
]
