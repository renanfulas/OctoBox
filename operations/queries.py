"""
ARQUIVO: snapshots de leitura do workspace operacional.

POR QUE ELE EXISTE:
- concentra a leitura operacional por papel fora de boxcore.operations.

O QUE ESTE ARQUIVO FAZ:
1. monta snapshots de owner, dev, manager e coach.
2. preserva consultas reutilizaveis fora da camada HTTP.

PONTOS CRITICOS:
- mudancas aqui afetam a leitura operacional por papel e a performance dessas telas.
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from finance.models import Payment, PaymentStatus
from monitoring.beacon_snapshot import build_red_beacon_snapshot
from monitoring.manager_realtime_metrics import build_manager_realtime_metrics_snapshot
from monitoring.student_realtime_metrics import build_student_realtime_metrics_snapshot
from operations.owner_workspace_queries import build_owner_workspace_snapshot as build_owner_workspace_snapshot_data
from operations.models import BehaviorCategory, ClassSession
from operations.manager_workspace_queries import build_manager_workspace_snapshot as build_manager_workspace_snapshot_data
from operations.reception_workspace_queries import build_reception_workspace_snapshot as build_reception_workspace_snapshot_data
from student_app.models import SessionWorkoutStatus


def _build_hero_stat(label, value):
    return {'label': label, 'value': value}


def _build_metric_card(card_class, eyebrow, value, note=None):
    card = {
        'card_class': card_class,
        'eyebrow': eyebrow,
        'display_value': value,
    }
    if note:
        card['note'] = note
    return card


def _build_decision_entry_context(entry_item=None, secondary_item=None):
    entry_item = entry_item or {}
    secondary_item = secondary_item or {}
    return {
        'entry_key': entry_item.get('key', ''),
        'entry_surface': entry_item.get('key', ''),
        'entry_href': entry_item.get('href', ''),
        'entry_href_label': entry_item.get('href_label', 'Abrir'),
        'entry_label': entry_item.get('label', ''),
        'entry_reason': entry_item.get('summary', ''),
        'entry_count': entry_item.get('count'),
        'entry_pill_class': entry_item.get('pill_class', 'accent'),
        'secondary_key': secondary_item.get('key', ''),
        'secondary_surface': secondary_item.get('key', ''),
        'secondary_href': secondary_item.get('href', ''),
        'secondary_href_label': secondary_item.get('href_label', 'Abrir'),
        'secondary_label': secondary_item.get('label', ''),
        'secondary_reason': secondary_item.get('summary', ''),
    }


def _serialize_attendance(attendance):
    return {
        'id': attendance.id,
        'student_id': attendance.student.id,
        'student_full_name': attendance.student.full_name,
        'status': attendance.status,
        'status_label': attendance.get_status_display(),
        'notes': attendance.notes,
        'check_in_url': reverse('attendance-action', args=[attendance.id, 'check-in']),
        'check_out_url': reverse('attendance-action', args=[attendance.id, 'check-out']),
        'absent_url': reverse('attendance-action', args=[attendance.id, 'absent']),
        'behavior_note_url': reverse('technical-behavior-note-create', args=[attendance.student.id]),
    }


def _serialize_coach_session(session):
    attendances = [_serialize_attendance(attendance) for attendance in session.attendances.all()]
    workout = getattr(session, 'workout', None)
    workout_status_label = workout.get_status_display() if workout else 'Sem WOD'
    if workout is None:
        workout_status_class = 'info'
        workout_action_label = 'Criar WOD'
    elif workout.status == SessionWorkoutStatus.PUBLISHED:
        workout_status_class = 'success'
        workout_action_label = 'Editar WOD'
    elif workout.status == SessionWorkoutStatus.PENDING_APPROVAL:
        workout_status_class = 'warning'
        workout_action_label = 'Revisar WOD'
    elif workout.status == SessionWorkoutStatus.REJECTED:
        workout_status_class = 'danger'
        workout_action_label = 'Ajustar WOD'
    else:
        workout_status_class = 'info'
        workout_action_label = 'Continuar WOD'
    return {
        'id': session.id,
        'title': session.title,
        'scheduled_at': session.scheduled_at,
        'duration_minutes': session.duration_minutes,
        'attendance_count': len(attendances),
        'attendances': attendances,
        'workout_editor_url': reverse('coach-session-workout-editor', args=[session.id]),
        'workout_status_label': workout_status_label,
        'workout_status_class': workout_status_class,
        'workout_action_label': workout_action_label,
    }


def _serialize_behavior_categories():
    return [{'value': value, 'label': label} for value, label in BehaviorCategory.choices]


def build_owner_workspace_snapshot(*, today):
    return build_owner_workspace_snapshot_data(today=today)


def build_dev_workspace_snapshot():
    red_beacon_snapshot = build_red_beacon_snapshot()
    technical_metrics = {
        'eventos_auditados': AuditEvent.objects.count(),
        'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
        'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
    }
    student_realtime_metrics = build_student_realtime_metrics_snapshot()
    manager_realtime_metrics = build_manager_realtime_metrics_snapshot()
    recent_audit_events = list(AuditEvent.objects.select_related('actor')[:10])
    return {
        'technical_metrics': technical_metrics,
        'student_realtime_metrics': student_realtime_metrics,
        'manager_realtime_metrics': manager_realtime_metrics,
        'red_beacon_snapshot': red_beacon_snapshot,
        'hero_stats': [
            _build_hero_stat('Auditados', technical_metrics['eventos_auditados']),
            _build_hero_stat('Ultimas 24h', technical_metrics['eventos_24h']),
            _build_hero_stat('Usuarios', technical_metrics['usuarios_com_papel']),
            _build_hero_stat('Realtime', student_realtime_metrics['events_total']),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card dev-steel', 'Eventos auditados', technical_metrics['eventos_auditados'], 'Historico total sensivel disponivel para investigacao, leitura forense e prova operacional.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos nas ultimas 24h', technical_metrics['eventos_24h'], 'Volume recente para avaliar movimentacao real e detectar ondas anormais de alteracao.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Usuarios com papel', technical_metrics['usuarios_com_papel'], 'Cobertura atual de contas com fronteira operacional definida no sistema.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos realtime', student_realtime_metrics['events_total'], 'Sinais SSE publicados para locks, financeiro, matricula e perfil do drawer de alunos.'),
            _build_metric_card('operation-kpi-card dev-steel', 'Streams ativos', student_realtime_metrics['active_streams'], 'Conexoes SSE vivas neste instante para observar concorrencia sem polling cego.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Conflitos de save', student_realtime_metrics['conflicts_total'], 'Tentativas bloqueadas por versao velha em vez de sobrescrever dado novo.'),
        ],
        'dev_operational_focus': [
            {
                'label': 'Comece pelo rastro recente',
                'chip_label': 'Auditoria',
                'summary': f"{technical_metrics['eventos_24h']} evento(s) nas ultimas 24h mostram se a investigacao deve comecar no agora ou no historico amplo.",
                'pill_class': 'warning' if technical_metrics['eventos_24h'] > 0 else 'success',
                'href': '#dev-audit-board',
                'href_label': 'Ver eventos recentes',
            },
            {
                'label': 'Depois valide a cobertura de acesso',
                'chip_label': 'Fronteiras',
                'summary': f"{technical_metrics['usuarios_com_papel']} usuario(s) com papel ajudam a medir se a fronteira operacional continua coerente.",
                'pill_class': 'info',
                'href': '#dev-boundary-board',
                'href_label': 'Ver fronteiras',
            },
            {
                'label': 'Feche com leitura sistemica',
                'chip_label': 'Rastros',
                'summary': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s) sustentam manutencao, investigacao e prova operacional sem virar chute tecnico.",
                'pill_class': 'accent',
                'href': '#dev-read-board',
                'href_label': 'Ver trilha curta',
            },
        ],
        'recent_audit_events': recent_audit_events,
        'dev_boundaries': [
            {
                'title': 'DEV investiga sem assumir a operacao',
                'copy': 'O papel tecnico mantem o sistema e investiga rastros, mas nao deve virar manager, recepcao ou coach por atalho.',
            },
            {
                'title': 'Leitura ampla, escrita minima',
                'copy': 'Quando houver manutencao, o caminho seguro e operar com rastreabilidade e o menor alcance de escrita necessario.',
            },
            {
                'title': 'Contingencia nao e rotina',
                'copy': 'Acesso elevado de emergencia fica fora do fluxo diario e precisa nascer com regra propria antes de existir.',
            },
        ],
        'dev_reads': [
            {
                'title': 'Mapa do sistema antes do mergulho',
                'copy': 'Comece pela arquitetura e pelo fluxo principal para nao investigar sintoma como se fosse causa raiz.',
            },
            {
                'title': 'Papeis e acessos como segunda camada',
                'copy': 'Revise as fronteiras de permissao antes de concluir que o problema esta na interface ou no dado.',
            },
            {
                'title': 'Auditoria por ultimo no recorte certo',
                'copy': 'Abra a trilha sensivel para confirmar ator, horario e alvo sem depender de memoria tecnica ou conversa paralela.',
            },
        ],
        'dev_table_guides': [
            {
                'title': 'Rastro que deve abrir a investigacao',
                'eyebrow': f"{technical_metrics['eventos_24h']} evento(s) nas ultimas 24h",
                'copy': 'Comece por aqui quando precisar localizar alteracao recente antes de abrir historico inteiro e perder tempo tecnico.',
            },
            {
                'title': 'Cobertura de fronteira atual',
                'eyebrow': f"{technical_metrics['usuarios_com_papel']} usuario(s) com papel",
                'copy': 'Use este ponto para validar se acesso continua com dono claro ou se alguma conta ja saiu da fronteira prevista.',
            },
            {
                'title': 'Base forense disponivel',
                'eyebrow': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s)",
                'copy': 'Esse volume sustenta manutencao e prova operacional sem depender de memoria tecnica, conversa paralela ou chute.',
            },
        ],
    }


def build_manager_workspace_snapshot(*, actor=None):
    return build_manager_workspace_snapshot_data(actor=actor)


def build_coach_workspace_snapshot(*, today):
    sessions = list(
        ClassSession.objects.filter(scheduled_at__date=today)
        .select_related('workout')
        .prefetch_related('attendances__student')
        .annotate(attendance_cnt=Count('attendances'))
        .order_by('scheduled_at')
    )
    for session in sessions:
        workout = getattr(session, 'workout', None)
        session.workout_editor_url = reverse('coach-session-workout-editor', args=[session.id])
        if workout is None:
            session.workout_status_label = 'Sem WOD'
            session.workout_status_class = 'info'
            session.workout_action_label = 'Criar WOD'
        elif workout.status == SessionWorkoutStatus.PUBLISHED:
            session.workout_status_label = 'Publicado'
            session.workout_status_class = 'success'
            session.workout_action_label = 'Editar WOD'
        elif workout.status == SessionWorkoutStatus.PENDING_APPROVAL:
            session.workout_status_label = 'Aguardando aprovacao'
            session.workout_status_class = 'warning'
            session.workout_action_label = 'Revisar WOD'
        elif workout.status == SessionWorkoutStatus.REJECTED:
            session.workout_status_label = 'Rejeitado'
            session.workout_status_class = 'danger'
            session.workout_action_label = 'Ajustar WOD'
        else:
            session.workout_status_label = 'Rascunho'
            session.workout_status_class = 'info'
            session.workout_action_label = 'Continuar WOD'
    total_attendances = sum(session.attendance_cnt for session in sessions)
    sessions_with_students = sum(1 for session in sessions if session.attendance_cnt > 0)
    pending_checkins = sum(max(session.attendance_cnt, 0) for session in sessions)
    coach_decision_entry_context = _build_decision_entry_context(
        {
            'key': 'sessions',
            'href': '#coach-sessions-board',
            'href_label': 'Ver aulas do dia',
            'label': 'Comece pela agenda de hoje',
            'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
            'count': len(sessions),
            'pill_class': 'info' if len(sessions) > 0 else 'success',
        },
        {
            'key': 'boundaries',
            'href': '#coach-boundary-board',
            'href_label': 'Ver limites da área',
            'label': 'Feche com ocorrências técnicas',
            'summary': f'{len(BehaviorCategory.choices)} categoria(s) cobrem o registro técnico sem misturar treino com financeiro ou recepção.',
        },
    )
    transport_payload = {
        'sessions_today': [_serialize_coach_session(session) for session in sessions],
        'behavior_categories': _serialize_behavior_categories(),
    }
    return {
        'sessions_today': sessions,
        'hero_stats': [
            _build_hero_stat('Aulas', len(sessions)),
            _build_hero_stat('Rotinas', 3),
            _build_hero_stat('Limites', 3),
            _build_hero_stat('Ocorrencias', len(BehaviorCategory.choices)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card coach-mint', 'Aulas do dia', len(sessions)),
            _build_metric_card('operation-kpi-card coach-indigo', 'Alunos na lista', total_attendances),
            _build_metric_card('operation-kpi-card coach-orange', 'Check-ins no turno', sessions_with_students),
            _build_metric_card('operation-kpi-card coach-orange', 'Pendencias de check-in', pending_checkins),
        ],
        'coach_operational_focus': [
            {
                'label': 'Comece pela agenda de hoje',
                'chip_label': 'Turmas',
                'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
                'count': len(sessions),
                'pill_class': 'info' if len(sessions) > 0 else 'success',
                'href': '#coach-sessions-board',
                'href_label': 'Ver aulas do dia',
            },
            {
                'label': 'Depois veja onde ja ha presenca real',
                'chip_label': 'Presenca',
                'summary': f'{sessions_with_students} turma(s) ja tem lista ativa e {total_attendances} presenca(s) para registrar sem ruido administrativo.',
                'count': sessions_with_students,
                'pill_class': 'accent',
                'href': '#coach-sessions-board',
                'href_label': 'Abrir rotina de presenca',
            },
        ],
        'coach_decision_entry_context': coach_decision_entry_context,
        'behavior_categories': BehaviorCategory.choices,
        'transport_payload': transport_payload,
    }


def build_reception_workspace_snapshot(*, today):
    return build_reception_workspace_snapshot_data(today=today)


__all__ = [
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_workspace_snapshot',
]

