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

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_OWNER
from operations.models import AttendanceStatus, SessionStatus
from student_app.models import (
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    WorkoutFollowUpStatus,
)

from .workout_board_builders import (
    build_management_alert_priority,
    build_management_recommendations,
    build_operational_leverage_summary,
    build_operational_leverage_trends,
    build_operational_management_alerts,
    build_operational_memory_patterns,
    build_weekly_executive_summary,
)


def _push_operational_action(actions, *, key, label, copy, tone='info', href=''):
    if any(action['key'] == key for action in actions):
        return
    actions.append(
        {
            'key': key,
            'label': label,
            'copy': copy,
            'tone': tone,
            'href': href,
        }
    )


def build_publication_runtime_metrics(*, session, workout):
    attendances = list(session.attendances.all())
    reserved_statuses = {
        AttendanceStatus.BOOKED,
        AttendanceStatus.CHECKED_IN,
        AttendanceStatus.CHECKED_OUT,
    }
    reserved_count = sum(1 for attendance in attendances if attendance.status in reserved_statuses)
    checked_in_count = sum(
        1 for attendance in attendances if attendance.status in {AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT}
    )
    viewer_count = len(list(workout.student_views.all()))
    viewer_rate = round((viewer_count / reserved_count) * 100) if reserved_count else 0
    return {
        'reserved_count': reserved_count,
        'checked_in_count': checked_in_count,
        'viewer_count': viewer_count,
        'viewer_rate': viewer_rate,
    }


def _collect_relevant_follow_up_alerts(*, action_key, alerts):
    alert_labels = [alert['label'] for alert in alerts]
    if action_key == 'whatsapp-reinforce':
        return [label for label in alert_labels if 'nenhuma abertura' in label.lower() or 'poucos alunos abriram' in label.lower()]
    if action_key == 'coach-align':
        return [label for label in alert_labels if 'urgente' in label.lower() or 'em aula' in label.lower()]
    if action_key == 'desk-follow-up':
        return [label for label in alert_labels if 'poucos alunos abriram' in label.lower() or 'em aula' in label.lower()]
    return alert_labels


def build_follow_up_result_summary(result, *, action_key, current_metrics, alerts):
    if result is None:
        return None
    baseline_metrics = result.baseline_metrics or {}
    resolved_by_label = ''
    if result.resolved_by is not None:
        resolved_by_label = result.resolved_by.get_full_name() or result.resolved_by.username
    resolved_at_label = timezone.localtime(result.resolved_at).strftime('%d/%m %H:%M') if result.resolved_at else ''
    status_tone = 'success' if result.status == WorkoutFollowUpStatus.COMPLETED else 'warning'
    relevant_alerts = _collect_relevant_follow_up_alerts(action_key=action_key, alerts=alerts)
    viewer_before = int(baseline_metrics.get('viewer_count') or 0)
    viewer_after = int(current_metrics.get('viewer_count') or 0)
    check_in_before = int(baseline_metrics.get('checked_in_count') or 0)
    check_in_after = int(current_metrics.get('checked_in_count') or 0)
    reserved_before = int(baseline_metrics.get('reserved_count') or 0)
    reserved_after = int(current_metrics.get('reserved_count') or 0)
    if result.status == WorkoutFollowUpStatus.DISMISSED:
        monitor_status = 'dismissed'
        monitor_label = 'Encerrado'
        monitor_tone = 'warning'
    elif not relevant_alerts:
        monitor_status = 'resolved'
        monitor_label = 'Resolvido'
        monitor_tone = 'success'
    elif viewer_after > viewer_before or check_in_after > check_in_before:
        monitor_status = 'monitoring'
        monitor_label = 'Monitorando'
        monitor_tone = 'accent'
    else:
        monitor_status = 'not_resolved'
        monitor_label = 'Nao resolveu'
        monitor_tone = 'danger'
    return {
        'status': result.status,
        'status_label': result.get_status_display(),
        'status_tone': status_tone,
        'outcome_note': result.outcome_note,
        'resolved_by_label': resolved_by_label,
        'resolved_at_label': resolved_at_label,
        'summary': (
            f"{result.get_status_display()} por {resolved_by_label} em {resolved_at_label}"
            if resolved_by_label and resolved_at_label
            else result.get_status_display()
        ),
        'monitor_status': monitor_status,
        'monitor_label': monitor_label,
        'monitor_tone': monitor_tone,
        'before_after_summary': (
            f'Aberturas {viewer_before}->{viewer_after} | Check-in {check_in_before}->{check_in_after} | Turma {reserved_before}->{reserved_after}'
        ),
        'delta_summary': (
            f"Aberturas {viewer_after - viewer_before:+d} | Check-in {check_in_after - check_in_before:+d}"
        ),
        'remaining_alerts': relevant_alerts[:3],
    }


def build_live_follow_up_escalation(*, runtime_label, reasons, actions, current_role_slug):
    lowered_reasons = ' '.join(reasons).lower()
    lowered_actions = ' '.join(actions).lower()
    if runtime_label == 'Aula em andamento' or 'em aula' in lowered_reasons:
        return {
            'owner_label': 'Recepcao' if current_role_slug == ROLE_OWNER else 'Operacao',
            'escalation_label': 'Escalonar agora no chao da operacao',
            'tone': 'danger',
            'href': reverse('reception-workspace') if current_role_slug == ROLE_OWNER else reverse('manager-workspace'),
        }
    if 'coach' in lowered_actions or 'urgencia' in lowered_reasons:
        return {
            'owner_label': 'Coach',
            'escalation_label': 'Escalonar para alinhamento com coach',
            'tone': 'warning',
            'href': '',
        }
    if 'whatsapp' in lowered_actions:
        return {
            'owner_label': 'WhatsApp',
            'escalation_label': 'Escalonar para reforco de comunicacao',
            'tone': 'accent',
            'href': reverse('whatsapp-workspace'),
        }
    return {
        'owner_label': 'Manager/Owner',
        'escalation_label': 'Escalonar para leitura executiva',
        'tone': 'info',
        'href': reverse('workout-approval-board'),
    }


def build_operational_memory_digest(memories):
    digest = []
    for memory in memories[:4]:
        actor_label = ''
        if memory.created_by is not None:
            actor_label = memory.created_by.get_full_name() or memory.created_by.username
        digest.append(
            {
                'kind_label': memory.get_kind_display(),
                'note': memory.note,
                'created_at_label': timezone.localtime(memory.created_at).strftime('%d/%m %H:%M'),
                'actor_label': actor_label,
            }
        )
    return digest


def build_executive_case_closure(*, runtime_label, alerts, follow_up_actions):
    has_open_action = False
    has_monitoring = False
    has_not_resolved = False
    for action in follow_up_actions:
        result = action.get('result')
        if result is None:
            has_open_action = True
            continue
        if result['monitor_status'] == 'monitoring':
            has_monitoring = True
        elif result['monitor_status'] == 'not_resolved':
            has_not_resolved = True

    if has_not_resolved or (alerts and runtime_label == 'Aula em andamento'):
        return {
            'status': 'strong_intervention',
            'label': 'Intervencao forte',
            'tone': 'danger',
            'summary': 'Esse caso ainda pede resposta forte da operacao para nao contaminar a experiencia da aula.',
        }
    if has_open_action:
        return {
            'status': 'awaiting_action',
            'label': 'Aguardando acao',
            'tone': 'warning',
            'summary': 'A leitura do risco ja existe, mas ainda falta uma resposta registrada para fechar o ciclo.',
        }
    if has_monitoring or alerts:
        return {
            'status': 'monitoring',
            'label': 'Acompanhando',
            'tone': 'accent',
            'summary': 'Ja houve resposta operacional, mas o caso ainda merece vigia curta antes de ser dado como absorvido.',
        }
    return {
        'status': 'absorbed',
        'label': 'Absorvido',
        'tone': 'success',
        'summary': 'A operacao absorveu o caso e nao ha sinal vivo pedindo nova escalada agora.',
    }


def build_publication_follow_up_actions(*, current_role_slug, approval_category, runtime_label, alerts):
    actions = []
    alert_labels = ' '.join(alert['label'] for alert in alerts).lower()
    if 'nenhuma abertura' in alert_labels or 'poucos alunos abriram' in alert_labels:
        _push_operational_action(
            actions,
            key='whatsapp-reinforce',
            label='Reforcar chamada no WhatsApp',
            copy='Acione a trilha de mensagens para lembrar a turma de abrir o WOD antes da aula.',
            tone='warning',
            href=reverse('whatsapp-workspace'),
        )
    if approval_category == 'operational_urgency' or 'em aula' in alert_labels:
        _push_operational_action(
            actions,
            key='coach-align',
            label='Avisar coach',
            copy='Alinhe rapido com o coach para confirmar se o treino precisa de reforco verbal ou ajuste de abordagem.',
            tone='info',
        )
    if 'poucos alunos abriram' in alert_labels or 'em aula' in alert_labels:
        _push_operational_action(
            actions,
            key='desk-follow-up',
            label='Acompanhar recepcao' if current_role_slug == ROLE_OWNER else 'Acompanhar operacao agora',
            copy='Monitore chegada, check-in e leitura do treino no chao da operacao antes da aula travar.',
            tone='accent',
            href=reverse('reception-workspace') if current_role_slug == ROLE_OWNER else reverse('manager-workspace'),
        )
    if runtime_label == 'Aula encerrada' and alerts:
        _push_operational_action(
            actions,
            key='next-cycle-review',
            label='Revisar no proximo ciclo',
            copy='Leve esse caso para a revisao do proximo WOD e ajuste a estrategia de publicacao ou reforco.',
            tone='info',
            href=reverse('workout-approval-board'),
        )
    return actions[:3]


def build_published_workout_history(*, limit=12, coach_username='', today_only=False, published_reason='', current_role_slug=''):
    now = timezone.localtime()
    queryset = (
        SessionWorkoutRevision.objects.select_related(
            'workout',
            'workout__session',
            'workout__session__coach',
            'created_by',
        )
        .prefetch_related(
            'workout__session__attendances',
            'workout__student_views',
            'workout__follow_up_actions',
            'workout__operational_memories__created_by',
        )
        .filter(event=SessionWorkoutRevisionEvent.PUBLISHED)
    )
    if coach_username:
        queryset = queryset.filter(workout__session__coach__username=coach_username)
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
            'is_sensitive_confirmation': bool(snapshot.get('approved_with_sensitive_confirmation')),
            'runtime_label': runtime_label,
            'runtime_tone': runtime_tone,
            'capacity': session.capacity,
            'reserved_count': reserved_count,
            'checked_in_count': checked_in_count,
            'viewer_count': viewer_count,
            'viewer_rate_label': f'{viewer_rate}%' if reserved_count else 'Sem base',
            'alerts': alerts,
            'has_alerts': bool(alerts),
            'alert_tone': highest_alert_tone or '',
            'follow_up_actions': follow_up_actions,
            'executive_closure': executive_closure,
            'operational_memories': build_operational_memory_digest(operational_memories),
            'operational_memory_kinds': operational_memory_kinds,
        }
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
    operational_management_priority = build_management_alert_priority(operational_management_alerts)
    operational_management_recommendations = build_management_recommendations(
        operational_management_priority['entries']
    )
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
            'weekly_executive_summary': weekly_executive_summary,
        },
    }
