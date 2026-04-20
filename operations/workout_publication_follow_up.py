"""
ARQUIVO: follow-up e escalation da leitura pos-publicacao do WOD.

POR QUE ELE EXISTE:
- tira de `workout_published_history.py` o corredor de resposta operacional.

O QUE ESTE ARQUIVO FAZ:
1. monta acoes sugeridas de follow-up.
2. resume o resultado operacional ja registrado.
3. calcula a escalada curta mais apropriada.

PONTOS CRITICOS:
- preservar labels, tom e shape de retorno usados pela board.
- manter esse corredor separado da leitura base do historico.
"""

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_OWNER
from student_app.models import WorkoutFollowUpStatus


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
