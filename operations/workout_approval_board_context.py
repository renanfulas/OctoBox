"""
ARQUIVO: coordenacao de contexto da board de aprovacao do WOD.

POR QUE ELE EXISTE:
- deixa a `WorkoutApprovalBoardView` como casca fina, mantendo a montagem de contexto fora da borda HTTP.

O QUE ESTE ARQUIVO FAZ:
1. monta fila pendente com filtros e ordenacao.
2. monta payload da pagina.
3. prepara a leitura curta da board de aprovacao.

PONTOS CRITICOS:
- manter o shape do contexto estavel para o template.
- nao duplicar regra de review snapshot fora do corredor oficial.
"""

from django.urls import reverse

from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload

from operations.forms import (
    WorkoutApprovalDecisionForm,
    WorkoutApprovalFilterForm,
    WorkoutRejectionForm,
)
from student_app.models import (
    SessionWorkout,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
)

from .workout_corridor_navigation import build_workout_corridor_tabs
from .workout_support import build_policy_badge_from_snapshot, build_workout_review_snapshot, extract_latest_policy_snapshot


def _build_pending_workouts(*, filter_form, today, build_review_snapshot):
    queryset = (
        SessionWorkout.objects.select_related('session', 'session__coach', 'submitted_by')
        .prefetch_related('blocks__movements', 'revisions')
        .filter(status=SessionWorkoutStatus.PENDING_APPROVAL)
    )
    selected_coach = ''
    selected_session_id = None
    sort_value = 'submitted_oldest'
    sensitive_only = False
    today_only = False
    published_reason = ''
    if filter_form.is_valid():
        selected_coach = (filter_form.cleaned_data.get('coach') or '').strip()
        selected_session_id = filter_form.cleaned_data.get('session_id')
        sort_value = filter_form.cleaned_data.get('sort') or 'submitted_oldest'
        sensitive_only = bool(filter_form.cleaned_data.get('sensitive_only'))
        today_only = bool(filter_form.cleaned_data.get('today_only'))
        published_reason = (filter_form.cleaned_data.get('published_reason') or '').strip()
        if selected_coach:
            queryset = queryset.filter(session__coach__username=selected_coach)
        if selected_session_id:
            queryset = queryset.filter(session_id=selected_session_id)
        if today_only:
            queryset = queryset.filter(session__scheduled_at__date=today)
        if sort_value == 'submitted_newest':
            queryset = queryset.order_by('-submitted_at', 'session__scheduled_at')
        elif sort_value == 'session_soonest':
            queryset = queryset.order_by('session__scheduled_at', 'submitted_at')
        else:
            queryset = queryset.order_by('submitted_at', 'session__scheduled_at')
    else:
        queryset = queryset.order_by('submitted_at', 'session__scheduled_at')

    pending_workouts = list(queryset)
    for workout in pending_workouts:
        workout.review_snapshot = build_review_snapshot(workout)
        workout.policy_badge = build_policy_badge_from_snapshot(
            extract_latest_policy_snapshot(workout, preferred_event=SessionWorkoutRevisionEvent.SUBMITTED)
        )
    if sensitive_only:
        pending_workouts = [workout for workout in pending_workouts if workout.review_snapshot['diff_snapshot']['is_sensitive']]
    pending_workouts.sort(
        key=lambda workout: (
            -workout.review_snapshot['decision_assist']['impact_score'],
            workout.session.scheduled_at,
            workout.submitted_at or workout.created_at,
        )
    )
    return {
        'pending_workouts': pending_workouts,
        'selected_coach': selected_coach,
        'selected_session_id': selected_session_id,
        'sort_value': sort_value,
        'sensitive_only': sensitive_only,
        'today_only': today_only,
        'published_reason': published_reason,
    }


def _build_coach_options():
    coach_options = []
    coach_pairs = (
        SessionWorkout.objects.select_related('session__coach')
        .filter(status=SessionWorkoutStatus.PENDING_APPROVAL, session__coach__isnull=False)
        .values_list('session__coach__username', 'session__coach__first_name', 'session__coach__last_name')
        .distinct()
    )
    for username, first_name, last_name in coach_pairs:
        label = f'{first_name} {last_name}'.strip() or username
        coach_options.append({'value': username, 'label': label})
    return coach_options


def _build_approval_inbox_items(pending_workouts):
    items = []
    for workout in pending_workouts:
        review_snapshot = workout.review_snapshot
        policy_badge = build_policy_badge_from_snapshot(
            extract_latest_policy_snapshot(workout, preferred_event=SessionWorkoutRevisionEvent.SUBMITTED)
        )
        items.append(
            {
                'workout_id': workout.id,
                'session_title': workout.session.title,
                'session_label': workout.session.scheduled_at.strftime('%d/%m %H:%M'),
                'coach_label': workout.session.coach.get_full_name() or workout.session.coach.username
                if workout.session.coach
                else 'Sem coach',
                'status_label': workout.get_status_display(),
                'impact_label': review_snapshot['decision_assist']['impact_label'],
                'impact_tone': review_snapshot['decision_assist']['impact_tone'],
                'is_sensitive': review_snapshot['diff_snapshot']['is_sensitive'],
                'requires_confirmation': review_snapshot['requires_confirmation'],
                'summary': review_snapshot['review_summary'],
                'policy_badge': policy_badge,
            }
        )
    return items


def _build_page_payload(*, page_title, page_subtitle, current_role_slug):
    return build_page_payload(
        context={
            'page_key': 'operations-workout-approval-board',
            'title': page_title,
            'subtitle': page_subtitle,
            'mode': 'workspace',
            'role_slug': current_role_slug,
        },
        data={
            'hero': build_page_hero(
                eyebrow='Aprovacao',
                title='Fila de WOD pendente.',
                copy='Aqui owner e manager fazem o carimbo final antes de o treino chegar ao aluno.',
                actions=[{'label': 'Voltar a operacao', 'href': reverse('role-operations'), 'kind': 'secondary'}],
                aria_label='Fila de aprovacao de WOD',
                classes=['coach-hero'],
                data_panel='coach-hero',
                actions_slot='coach-hero-actions',
            ),
        },
        behavior={
            'surface_key': 'operations-workout-approval-board',
            'scope': 'operations-approval',
        },
        assets=build_page_assets(
            css=[
                'css/design-system/operations.css',
                'css/design-system/operations/workspace/wod-inbox.css',
                'css/design-system/operations/workspace/wod-command-palette.css',
            ],
            deferred_js=[
                'js/operations/wod_inbox.js',
                'js/operations/wod_command_palette.js',
            ],
        ),
    )


def build_workout_approval_board_context(
    *,
    request,
    today,
    current_role,
    page_title,
    page_subtitle,
):
    filter_form = WorkoutApprovalFilterForm(request.GET or None)
    pending_state = _build_pending_workouts(
        filter_form=filter_form,
        today=today,
        build_review_snapshot=build_workout_review_snapshot,
    )
    pending_workouts = pending_state['pending_workouts']
    return {
        'operation_page_payload': _build_page_payload(
            page_title=page_title,
            page_subtitle=page_subtitle,
            current_role_slug=current_role.slug,
        ),
        'workout_corridor_tabs': build_workout_corridor_tabs(
            current_key='approval',
            current_role_slug=current_role.slug,
        ),
        'pending_workouts': pending_workouts,
        'approval_inbox_items': _build_approval_inbox_items(pending_workouts),
        'rejection_form': WorkoutRejectionForm(),
        'approval_decision_form': WorkoutApprovalDecisionForm(),
        'approval_filter_form': filter_form,
        'approval_queue_assist': {
            'total': len(pending_workouts),
            'batch_safe_count': sum(
                1 for workout in pending_workouts if not workout.review_snapshot['diff_snapshot']['is_sensitive']
            ),
            'high_impact_count': sum(
                1 for workout in pending_workouts if workout.review_snapshot['decision_assist']['impact_label'] == 'Alto impacto'
            ),
            'sensitive_count': sum(
                1 for workout in pending_workouts if workout.review_snapshot['diff_snapshot']['is_sensitive']
            ),
        },
        'approval_filter_state': {
            'sort': pending_state['sort_value'],
            'coach': pending_state['selected_coach'],
            'session_id': pending_state['selected_session_id'],
            'sensitive_only': pending_state['sensitive_only'],
            'today_only': pending_state['today_only'],
            'published_reason': pending_state['published_reason'],
        },
        'approval_coach_options': _build_coach_options(),
        'current_surface_path': request.get_full_path(),
    }
