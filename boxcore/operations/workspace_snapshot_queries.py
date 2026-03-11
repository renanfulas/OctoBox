"""
ARQUIVO: queries dos snapshots de workspace operacional por papel.

POR QUE ELE EXISTE:
- Centraliza leituras e snapshots usados pelas areas de Owner, DEV, Manager e Coach.

O QUE ESTE ARQUIVO FAZ:
1. Monta snapshots executivos, tecnicos, gerenciais e de aula.
2. Reaproveita consultas pesadas fora da camada HTTP.
3. Mantem as views operacionais focadas em permissao, request e resposta.

PONTOS CRITICOS:
- Mudancas aqui afetam a leitura operacional por papel e podem degradar performance se mal feitas.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from boxcore.models import (
    AuditEvent,
    BehaviorCategory,
    ClassSession,
    IntakeStatus,
    Payment,
    PaymentStatus,
    Student,
    StudentIntake,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)


def build_owner_workspace_snapshot(*, today):
    return {
        'headline_metrics': {
            'students': Student.objects.count(),
            'pending_intakes': StudentIntake.objects.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING]).count(),
            'whatsapp_contacts': WhatsAppContact.objects.count(),
            'messages_logged': WhatsAppMessageLog.objects.count(),
            'overdue_payments': Payment.objects.filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE], due_date__lt=today).count(),
        },
        'decision_board': [
            'Central de entrada pronta para receber alunos antes do cadastro definitivo.',
            'Base de WhatsApp pronta para armazenar contatos, vínculo e logs.',
            'Permissões reais por papel já separadas em áreas operacionais.',
        ],
    }


def build_dev_workspace_snapshot():
    return {
        'technical_metrics': {
            'eventos_auditados': AuditEvent.objects.count(),
            'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
            'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
        },
        'recent_audit_events': AuditEvent.objects.select_related('actor')[:10],
        'dev_boundaries': [
            'DEV investiga e mantém o sistema, mas não assume rotina de manager ou coach.',
            'O papel técnico deve operar com leitura ampla e escrita mínima, sempre com rastreabilidade.',
            'Acesso GOD continua fora da rotina e deve nascer depois com regra de contingência.',
        ],
    }


def build_manager_workspace_snapshot():
    return {
        'pending_intakes': StudentIntake.objects.select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:8],
        'unlinked_whatsapp': WhatsAppContact.objects.filter(status=WhatsAppContactStatus.NEW, linked_student__isnull=True).order_by('display_name', 'phone')[:8],
        'financial_alerts': Payment.objects.select_related('student').filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).order_by('due_date')[:8],
        'payments_without_enrollment': Payment.objects.select_related('student').filter(
            enrollment__isnull=True,
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date')[:8],
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
    }


def build_coach_workspace_snapshot(*, today):
    sessions = ClassSession.objects.filter(scheduled_at__date=today).prefetch_related('attendances__student').order_by('scheduled_at')
    return {
        'sessions_today': sessions,
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