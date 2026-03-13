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
from django.utils import timezone

from auditing.models import AuditEvent
from communications.queries import (
    build_communications_headline_metrics,
    get_pending_intakes,
    get_unlinked_whatsapp_contacts,
)
from finance.models import Payment, PaymentStatus
from operations.models import BehaviorCategory, ClassSession
from students.models import Student


def _build_hero_stat(label, value):
    return {'label': label, 'value': value}


def _build_metric_card(card_class, eyebrow, value, note):
    return {
        'card_class': card_class,
        'eyebrow': eyebrow,
        'display_value': value,
        'note': note,
    }


def build_owner_workspace_snapshot(*, today):
    communications_metrics = build_communications_headline_metrics(today=today)
    headline_metrics = {
        'students': Student.objects.count(),
        'pending_intakes': communications_metrics['pending_intakes'],
        'whatsapp_contacts': communications_metrics['whatsapp_contacts'],
        'messages_logged': communications_metrics['messages_logged'],
        'overdue_payments': Payment.objects.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
            due_date__lt=today,
        ).count(),
    }
    return {
        'headline_metrics': headline_metrics,
        'hero_stats': [
            _build_hero_stat('Base ativa', headline_metrics['students']),
            _build_hero_stat('Entradas', headline_metrics['pending_intakes']),
            _build_hero_stat('Atrasos', headline_metrics['overdue_payments']),
            _build_hero_stat('WhatsApp', headline_metrics['whatsapp_contacts']),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card owner-amber', 'Alunos registrados', headline_metrics['students'], 'Tamanho da base principal que sustenta presença, retenção e receita.'),
            _build_metric_card('operation-kpi-card owner-blue', 'Entradas pendentes', headline_metrics['pending_intakes'], 'Leads e cadastros provisórios que ainda pedem conversão ou revisão.'),
            _build_metric_card('operation-kpi-card owner-green', 'Contatos no WhatsApp', headline_metrics['whatsapp_contacts'], 'Capilaridade do canal de conversa pronta para vínculo operacional.'),
            _build_metric_card('operation-kpi-card owner-slate', 'Mensagens logadas', headline_metrics['messages_logged'], 'Histórico acumulado para rastrear relacionamento e futuras automações.'),
            _build_metric_card('operation-kpi-card owner-amber', 'Cobranças em atraso', headline_metrics['overdue_payments'], 'Sinal direto da pressão financeira que já exige leitura de retenção.'),
        ],
        'decision_board': [
            'Central de entrada pronta para receber alunos antes do cadastro definitivo.',
            'Base de WhatsApp pronta para armazenar contatos, vínculo e logs.',
            'Permissões reais por papel já separadas em áreas operacionais.',
        ],
        'decision_board_count_label': '3 frentes',
        'owner_reading_order': [
            'Comece pela fila de entrada e confira se o funil continua girando sem acúmulo indevido.',
            'Olhe os atrasos financeiros para medir risco de caixa e necessidade de ação de retenção.',
            'Use a base de WhatsApp e os logs como termômetro da maturidade operacional do produto.',
        ],
    }


def build_dev_workspace_snapshot():
    technical_metrics = {
        'eventos_auditados': AuditEvent.objects.count(),
        'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
        'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
    }
    recent_audit_events = list(AuditEvent.objects.select_related('actor')[:10])
    return {
        'technical_metrics': technical_metrics,
        'hero_stats': [
            _build_hero_stat('Auditados', technical_metrics['eventos_auditados']),
            _build_hero_stat('Últimas 24h', technical_metrics['eventos_24h']),
            _build_hero_stat('Usuários', technical_metrics['usuarios_com_papel']),
            _build_hero_stat('Auditoria', len(recent_audit_events)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card dev-steel', 'Eventos auditados', technical_metrics['eventos_auditados'], 'Histórico total sensível disponível para investigação, leitura forense e prova operacional.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos nas últimas 24h', technical_metrics['eventos_24h'], 'Volume recente para avaliar movimentação real e detectar ondas anormais de alteração.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Usuários com papel', technical_metrics['usuarios_com_papel'], 'Cobertura atual de contas com fronteira operacional definida no sistema.'),
        ],
        'recent_audit_events': recent_audit_events,
        'dev_boundaries': [
            'DEV investiga e mantém o sistema, mas não assume rotina de manager ou coach.',
            'O papel técnico deve operar com leitura ampla e escrita mínima, sempre com rastreabilidade.',
            'Acesso GOD continua fora da rotina e deve nascer depois com regra de contingência.',
        ],
        'dev_reads': [
            'Mapa do sistema para entender arquitetura e fluxo.',
            'Papéis e acessos para revisar fronteiras de permissão.',
            'Trilha de auditoria para investigar ações sensíveis recentes.',
        ],
    }


def build_manager_workspace_snapshot():
    pending_intakes = get_pending_intakes(limit=8)
    unlinked_whatsapp = get_unlinked_whatsapp_contacts(limit=8)
    financial_alerts = Payment.objects.select_related('student').filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]
    ).order_by('due_date')[:8]
    payments_without_enrollment = Payment.objects.select_related('student').filter(
        enrollment__isnull=True,
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).order_by('due_date')[:8]
    return {
        'pending_intakes': pending_intakes,
        'unlinked_whatsapp': unlinked_whatsapp,
        'financial_alerts': financial_alerts,
        'payments_without_enrollment': payments_without_enrollment,
        'hero_stats': [
            _build_hero_stat('Entradas', len(pending_intakes)),
            _build_hero_stat('WhatsApp', len(unlinked_whatsapp)),
            _build_hero_stat('Sem vínculo', len(payments_without_enrollment)),
            _build_hero_stat('Alertas', len(financial_alerts)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Entradas pendentes', len(pending_intakes), 'Pessoas que já chegaram ao sistema, mas ainda exigem triagem ou conversão.'),
            _build_metric_card('operation-kpi-card manager-sky', 'Contatos sem vínculo', len(unlinked_whatsapp), 'Conversas abertas que ainda precisam ser conectadas ao aluno principal.'),
            _build_metric_card('operation-kpi-card manager-gold', 'Pagamentos sem matrícula', len(payments_without_enrollment), 'Cobranças que podem contaminar leitura financeira enquanto não forem vinculadas.'),
            _build_metric_card('operation-kpi-card manager-steel', 'Alertas financeiros', len(financial_alerts), 'Fila de inadimplência e pendências para agir antes de escalar o problema.'),
        ],
        'manager_steps': [
            'Revisar entradas vindas de CSV, WhatsApp ou cadastro manual.',
            'Vincular contatos ao aluno definitivo quando houver match.',
            'Acompanhar inadimplência e preparar ações de retenção.',
        ],
        'manager_boundaries': [
            'Esta área não executa presença de aula em nome do coach.',
            'O foco aqui é entrada, vínculo, retenção e rotina financeira.',
            'A operação técnica do treino continua isolada na área do coach.',
        ],
        'manager_whatsapp_ready': [
            'Contato pode existir antes do aluno definitivo.',
            'Contato pode ser vinculado depois ao cadastro principal.',
            'Logs de mensagens podem ser armazenados sem quebrar o modelo atual.',
        ],
    }


def build_coach_workspace_snapshot(*, today):
    sessions = ClassSession.objects.filter(scheduled_at__date=today).prefetch_related('attendances__student').order_by('scheduled_at')
    return {
        'sessions_today': sessions,
        'hero_stats': [
            _build_hero_stat('Aulas', len(sessions)),
            _build_hero_stat('Rotinas', 3),
            _build_hero_stat('Limites', 3),
            _build_hero_stat('Ocorrências', len(BehaviorCategory.choices)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card coach-mint', 'Aulas do dia', len(sessions), 'Quantidade de turmas que o coach precisa enxergar e conduzir hoje.'),
            _build_metric_card('operation-kpi-card coach-indigo', 'Guias de execução', 3, 'Passos operacionais para manter presença, saída e falta registradas corretamente.'),
            _build_metric_card('operation-kpi-card coach-orange', 'Fronteiras do papel', 3, 'Lembrete visual do que pertence ao coach e do que continua fora desta área.'),
        ],
        'coach_notes': [
            'Use check-in ao iniciar presença real do aluno.',
            'Use check-out ao encerrar a aula ou saída do aluno.',
            'Use falta quando a reserva existia e o aluno não compareceu.',
        ],
        'behavior_categories': BehaviorCategory.choices,
        'coach_boundaries': [
            'Esta área não mostra fila financeira nem central de entrada.',
            'O foco do coach aqui é turma, presença e leitura do dia.',
            'Ocorrências técnicas podem ser registradas sem expor dados administrativos.',
        ],
    }


__all__ = [
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
]