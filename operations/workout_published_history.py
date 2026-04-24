"""
ARQUIVO: leitura publicada e follow-up executivo da board de WOD.

POR QUE ELE EXISTE:
- tira de `workspace_views.py` o corredor mais denso da board de aprovacao.

O QUE ESTE ARQUIVO FAZ:
1. le revisoes publicadas do WOD.
2. calcula runtime de consumo do treino e alertas pos-publicacao.
3. cruza follow-up, memoria operacional e closure executivo.
4. monta o historico publicado e o assistente executivo da board.

PONTOS CRITICOS:
- qualquer mudanca aqui afeta a leitura pos-publicacao do WOD.
- manter queries, agregacao e heuristica neste corredor, nao na borda HTTP.
"""

from datetime import timedelta

from django.utils import timezone

from operations.models import SessionStatus
from student_app.models import (
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
)

from .workout_publication_executive import (
    build_executive_case_closure,
    build_operational_memory_digest,
)
from .workout_publication_follow_up import (
    _push_operational_action,
    build_follow_up_result_summary,
    build_live_follow_up_escalation,
    build_publication_follow_up_actions,
)
from .workout_publication_metrics import (
    build_publication_rm_readiness,
    build_publication_runtime_metrics,
)
from .workout_support import build_policy_badge_from_snapshot
from .workout_board_builders import (
    build_rm_gap_queue,
    build_management_alert_priority,
    build_management_recommendations,
    build_rm_readiness_management_alerts,
    build_operational_leverage_summary,
    build_operational_leverage_trends,
    build_operational_management_alerts,
    build_operational_memory_patterns,
    build_weekly_executive_summary,
)


def build_published_workout_history(
    *,
    limit=12,
    coach_username='',
    today_only=False,
    published_reason='',
    current_role_slug='',
    session_id=None,
):
    now = timezone.localtime()
    queryset = (
        SessionWorkoutRevision.objects.select_related(
            'workout',
            'workout__session',
            'workout__session__coach',
            'created_by',
        )
        .prefetch_related(
            'workout__session__attendances__student',
            'workout__student_views',
            'workout__follow_up_actions',
            'workout__operational_memories__created_by',
            'workout__rm_gap_actions__updated_by',
        )
        .filter(event=SessionWorkoutRevisionEvent.PUBLISHED)
    )
    if coach_username:
        queryset = queryset.filter(workout__session__coach__username=coach_username)
    if session_id:
        queryset = queryset.filter(workout__session_id=session_id)
    if today_only:
        queryset = queryset.filter(workout__session__scheduled_at__date=now.date())
    if published_reason and published_reason != 'no_reason':
        queryset = queryset.filter(snapshot__approval_reason_category=published_reason)

    published_revisions = list(queryset.order_by('-created_at', '-id')[: max(limit * 3, limit)])
    category_counts = {
        'without_concerns': 0,
        'verbal_alignment': 0,
        'operational_urgency': 0,
        'no_reason': 0,
    }
    tone_map = {
        'without_concerns': 'success',
        'verbal_alignment': 'info',
        'operational_urgency': 'warning',
        'no_reason': 'accent',
    }
    history_items = []
    alert_spotlight = []
    suggested_actions = []
    critical_alert_count = 0
    warning_alert_count = 0
    resolved_action_count = 0
    open_action_count = 0
    resolved_outcome_count = 0
    monitoring_outcome_count = 0
    not_resolved_outcome_count = 0
    short_escalation_count = 0
    absorbed_case_count = 0
    monitoring_case_count = 0
    awaiting_action_case_count = 0
    strong_intervention_case_count = 0
    rm_ready_total = 0
    rm_required_total = 0
    rm_viewer_ready_total = 0
    rm_viewer_gap_total = 0
    for revision in published_revisions:
        snapshot = revision.snapshot or {}
        approval_category = snapshot.get('approval_reason_category') or 'no_reason'
        if published_reason == 'no_reason' and approval_category != 'no_reason':
            continue
        approval_label = snapshot.get('approval_reason_label') or 'Sem motivo extra'
        approval_summary = snapshot.get('approval_reason_summary') or 'Publicado sem observacao adicional registrada.'
        category_counts[approval_category] = category_counts.get(approval_category, 0) + 1

        published_by_label = ''
        if revision.created_by is not None:
            published_by_label = revision.created_by.get_full_name() or revision.created_by.username

        coach_label = 'Equipe OctoBox'
        if revision.workout.session.coach is not None:
            coach_label = revision.workout.session.coach.get_full_name() or revision.workout.session.coach.username

        session = revision.workout.session
        starts_at = timezone.localtime(session.scheduled_at)
        ends_at = starts_at + timedelta(minutes=session.duration_minutes)
        if session.status == SessionStatus.CANCELED:
            runtime_label = 'Aula cancelada'
            runtime_tone = 'danger'
        elif now < starts_at:
            runtime_label = 'Aula vai comecar'
            runtime_tone = 'accent'
        elif starts_at <= now <= ends_at and session.status in {SessionStatus.SCHEDULED, SessionStatus.OPEN}:
            runtime_label = 'Aula em andamento'
            runtime_tone = 'warning'
        else:
            runtime_label = 'Aula encerrada'
            runtime_tone = 'success'

        metrics = build_publication_runtime_metrics(session=session, workout=revision.workout)
        rm_readiness = build_publication_rm_readiness(snapshot=snapshot, session=session, workout=revision.workout)
        reserved_count = metrics['reserved_count']
        checked_in_count = metrics['checked_in_count']
        viewer_count = metrics['viewer_count']
        viewer_rate = metrics['viewer_rate']
        hours_until_start = (starts_at - now).total_seconds() / 3600
        alerts = []
        highest_alert_tone = ''

        def _push_alert(*, tone, label):
            nonlocal highest_alert_tone, critical_alert_count, warning_alert_count
            alerts.append({'tone': tone, 'label': label})
            if tone == 'danger':
                critical_alert_count += 1
                highest_alert_tone = 'danger'
            elif highest_alert_tone != 'danger':
                highest_alert_tone = 'warning'
                warning_alert_count += 1

        if approval_category == 'operational_urgency' and viewer_count == 0:
            _push_alert(tone='danger', label='WOD urgente publicado sem nenhuma abertura no app do aluno')
        elif approval_category == 'operational_urgency' and reserved_count and viewer_rate < 50:
            _push_alert(tone='warning', label='WOD urgente com consumo abaixo de 50% da turma reservada')

        if 0 <= hours_until_start <= 2 and reserved_count and viewer_rate < 50:
            _push_alert(tone='warning', label='Aula comeca em breve e poucos alunos abriram o WOD')

        if runtime_label == 'Aula em andamento' and checked_in_count > viewer_count:
            _push_alert(tone='warning', label='Ja ha aluno em aula sem leitura equivalente do WOD no app')

        if runtime_label == 'Aula encerrada' and reserved_count and viewer_count == 0:
            _push_alert(tone='warning', label='Aula encerrada sem nenhuma abertura registrada do WOD')
        if rm_readiness['has_percentage_rm'] and reserved_count and rm_readiness['fully_ready_count'] == 0:
            _push_alert(tone='danger', label='WOD com %RM sem nenhum aluno pronto com RM completo na turma reservada')
        elif rm_readiness['has_percentage_rm'] and reserved_count and rm_readiness['alert_level'] == 'warning':
            _push_alert(tone='warning', label='WOD com %RM e cobertura curta de RM na turma reservada')
        if rm_readiness['viewer_without_full_rm_count']:
            _push_alert(tone='warning', label='Aluno abriu o WOD, mas parte da turma seguiu sem RM completo para consumir a prescricao')

        existing_follow_up_results = {
            result.action_key: result for result in revision.workout.follow_up_actions.all()
        }
        follow_up_actions = build_publication_follow_up_actions(
            current_role_slug=current_role_slug,
            approval_category=approval_category,
            runtime_label=runtime_label,
            alerts=alerts,
        )
        known_action_keys = {action['key'] for action in follow_up_actions}
        for action_key, existing_result in existing_follow_up_results.items():
            if action_key in known_action_keys:
                continue
            follow_up_actions.append(
                {
                    'key': action_key,
                    'label': existing_result.action_label,
                    'copy': 'Retorno operacional ja registrado para esta acao.',
                    'tone': 'info',
                    'href': '',
                }
            )
        for action in follow_up_actions:
            result_summary = build_follow_up_result_summary(
                existing_follow_up_results.get(action['key']),
                action_key=action['key'],
                current_metrics=metrics,
                alerts=alerts,
            )
            action['result'] = result_summary
            action['is_resolved'] = bool(result_summary)
            if result_summary:
                resolved_action_count += 1
                if result_summary['monitor_status'] == 'resolved':
                    resolved_outcome_count += 1
                elif result_summary['monitor_status'] == 'monitoring':
                    monitoring_outcome_count += 1
                elif result_summary['monitor_status'] == 'not_resolved':
                    not_resolved_outcome_count += 1
            else:
                open_action_count += 1

        executive_closure = build_executive_case_closure(
            runtime_label=runtime_label,
            alerts=alerts,
            follow_up_actions=follow_up_actions,
        )
        if executive_closure['status'] == 'absorbed':
            absorbed_case_count += 1
        elif executive_closure['status'] == 'monitoring':
            monitoring_case_count += 1
        elif executive_closure['status'] == 'awaiting_action':
            awaiting_action_case_count += 1
        elif executive_closure['status'] == 'strong_intervention':
            strong_intervention_case_count += 1

        operational_memories = list(revision.workout.operational_memories.all())
        operational_memory_kinds = [memory.kind for memory in operational_memories]
        rm_gap_action_records = list(revision.workout.rm_gap_actions.all())
        policy_badge = build_policy_badge_from_snapshot(snapshot)
        history_item = {
            'workout_id': revision.workout_id,
            'session_title': session.title,
            'session_scheduled_label': starts_at.strftime('%d/%m %H:%M'),
            'published_at': timezone.localtime(revision.created_at),
            'workout_title': snapshot.get('title') or revision.workout.title or revision.workout.session.title,
            'version': revision.version,
            'published_at_label': timezone.localtime(revision.created_at).strftime('%d/%m %H:%M'),
            'published_by_label': published_by_label,
            'coach_label': coach_label,
            'approval_label': approval_label,
            'approval_summary': approval_summary,
            'approval_tone': tone_map.get(approval_category, 'accent'),
            'policy_badge': policy_badge,
            'is_sensitive_confirmation': bool(snapshot.get('approved_with_sensitive_confirmation')),
            'runtime_label': runtime_label,
            'runtime_tone': runtime_tone,
            'capacity': session.capacity,
            'reserved_count': reserved_count,
            'checked_in_count': checked_in_count,
            'viewer_count': viewer_count,
            'viewer_rate_label': f'{viewer_rate}%' if reserved_count else 'Sem base',
            'rm_readiness': rm_readiness,
            'alerts': alerts,
            'has_alerts': bool(alerts),
            'alert_tone': highest_alert_tone or '',
            'follow_up_actions': follow_up_actions,
            'executive_closure': executive_closure,
            'operational_memories': build_operational_memory_digest(operational_memories),
            'operational_memory_kinds': operational_memory_kinds,
            'rm_gap_action_records': rm_gap_action_records,
        }
        if rm_readiness['has_percentage_rm']:
            rm_ready_total += rm_readiness['fully_ready_count']
            rm_required_total += reserved_count
            rm_viewer_ready_total += rm_readiness['viewer_ready_count']
            rm_viewer_gap_total += rm_readiness['viewer_without_full_rm_count']
        history_items.append(history_item)
        if alerts and len(alert_spotlight) < 4:
            alert_spotlight.append(
                {
                    'tone': highest_alert_tone or 'warning',
                    'session_title': session.title,
                    'workout_title': history_item['workout_title'],
                    'label': alerts[0]['label'],
                }
            )
        for action in follow_up_actions:
            _push_operational_action(
                suggested_actions,
                key=action['key'],
                label=action['label'],
                copy=action['copy'],
                tone=action['tone'],
                href=action['href'],
            )

    history_items = history_items[:limit]
    operational_memory_summary = build_operational_memory_patterns(history_items=history_items)
    operational_leverage_summary = build_operational_leverage_summary(history_items=history_items)
    operational_leverage_trends = build_operational_leverage_trends(history_items=history_items)
    operational_management_alerts = build_operational_management_alerts(
        trend_cards=operational_leverage_trends['cards']
    )
    operational_management_alerts.extend(build_rm_readiness_management_alerts(history_items=history_items))
    operational_management_priority = build_management_alert_priority(operational_management_alerts)
    operational_management_recommendations = build_management_recommendations(
        operational_management_priority['entries']
    )
    rm_gap_queue = build_rm_gap_queue(history_items=history_items)
    weekly_executive_summary = build_weekly_executive_summary(
        history_items=history_items,
        management_priority=operational_management_priority,
        recommendations=operational_management_recommendations,
        trend_cards=operational_leverage_trends['cards'],
        now=now,
    )
    live_follow_up_entries = []
    for item in history_items:
        live_reasons = [alert['label'] for alert in item['alerts']]
        next_actions = []
        for action in item['follow_up_actions']:
            result = action.get('result')
            if result is None:
                next_actions.append(action['label'])
            elif result['monitor_status'] in {'monitoring', 'not_resolved'}:
                next_actions.append(action['label'])
                live_reasons.extend(result.get('remaining_alerts', []))
        if not live_reasons and not next_actions:
            continue
        escalation = build_live_follow_up_escalation(
            runtime_label=item['runtime_label'],
            reasons=live_reasons,
            actions=next_actions,
            current_role_slug=current_role_slug,
        )
        short_escalation_count += 1
        live_follow_up_entries.append(
            {
                'session_title': item['session_title'],
                'workout_title': item['workout_title'],
                'runtime_label': item['runtime_label'],
                'runtime_tone': item['runtime_tone'],
                'approval_label': item['approval_label'],
                'reasons': list(dict.fromkeys(live_reasons))[:3],
                'actions': list(dict.fromkeys(next_actions))[:2],
                'published_at_label': item['published_at_label'],
                'escalation': escalation,
                'executive_closure': item['executive_closure'],
            }
        )

    return {
        'entries': history_items,
        'live_follow_up_entries': live_follow_up_entries[:6],
        'assist': {
            'total': len(history_items),
            'without_concerns_count': category_counts.get('without_concerns', 0),
            'verbal_alignment_count': category_counts.get('verbal_alignment', 0),
            'operational_urgency_count': category_counts.get('operational_urgency', 0),
            'no_reason_count': category_counts.get('no_reason', 0),
            'viewer_total': sum(item['viewer_count'] for item in history_items),
            'reserved_total': sum(item['reserved_count'] for item in history_items),
            'rm_ready_total': rm_ready_total,
            'rm_required_total': rm_required_total,
            'rm_viewer_ready_total': rm_viewer_ready_total,
            'rm_viewer_gap_total': rm_viewer_gap_total,
            'critical_alert_count': critical_alert_count,
            'warning_alert_count': warning_alert_count,
            'resolved_action_count': resolved_action_count,
            'open_action_count': open_action_count,
            'resolved_outcome_count': resolved_outcome_count,
            'monitoring_outcome_count': monitoring_outcome_count,
            'not_resolved_outcome_count': not_resolved_outcome_count,
            'live_follow_up_count': len(live_follow_up_entries),
            'short_escalation_count': short_escalation_count,
            'absorbed_case_count': absorbed_case_count,
            'monitoring_case_count': monitoring_case_count,
            'awaiting_action_case_count': awaiting_action_case_count,
            'strong_intervention_case_count': strong_intervention_case_count,
            'alert_spotlight': alert_spotlight,
            'suggested_actions': suggested_actions[:4],
            'operational_memory_summary': operational_memory_summary,
            'operational_leverage_summary': operational_leverage_summary,
            'operational_leverage_trends': operational_leverage_trends,
            'operational_management_alerts': operational_management_alerts,
            'operational_management_priority': operational_management_priority,
            'operational_management_recommendations': operational_management_recommendations,
            'rm_gap_queue': rm_gap_queue,
            'weekly_executive_summary': weekly_executive_summary,
        },
    }
