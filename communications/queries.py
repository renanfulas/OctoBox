"""
ARQUIVO: consultas de leitura do dominio communications.

POR QUE ELE EXISTE:
- Tira leituras de intake e WhatsApp de modulos genericamente operacionais e da camada HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Resume metricas de entradas e contatos.
2. Expoe listas curtas para workspaces operacionais.
3. Centraliza contagens usadas em navegacao e alertas globais.

PONTOS CRITICOS:
- Essas consultas alimentam menus e snapshots de operacao; qualquer regressao aparece rapido na leitura do produto.
"""

from communications.models import IntakeStatus, StudentIntake, WhatsAppContact, WhatsAppContactStatus, WhatsAppMessageLog


def count_pending_intakes():
    return StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING],
        linked_student__isnull=True,
    ).count()


def count_whatsapp_contacts():
    return WhatsAppContact.objects.count()


def count_messages_logged():
    return WhatsAppMessageLog.objects.count()


def build_communications_headline_metrics(*, today):
    return {
        'pending_intakes': StudentIntake.objects.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING]).count(),
        'whatsapp_contacts': count_whatsapp_contacts(),
        'messages_logged': count_messages_logged(),
    }


def get_pending_intakes(*, limit=8):
    return StudentIntake.objects.select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:limit]


def get_unlinked_whatsapp_contacts(*, limit=8):
    return WhatsAppContact.objects.filter(
        status=WhatsAppContactStatus.NEW,
        linked_student__isnull=True,
    ).order_by('display_name', 'phone')[:limit]
