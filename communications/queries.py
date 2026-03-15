"""
ARQUIVO: consultas de leitura do dominio communications.

POR QUE ELE EXISTE:
- Centraliza leituras de WhatsApp e compoe metricas cruzadas usadas no shell e na operacao.

O QUE ESTE ARQUIVO FAZ:
1. Resume metricas de WhatsApp e funis relacionados.
2. Expoe listas curtas de contatos para workspaces operacionais.
3. Mantem compatibilidade enquanto intake termina de migrar para onboarding.

PONTOS CRITICOS:
- Essas consultas alimentam menus e snapshots de operacao; qualquer regressao aparece rapido na leitura do produto.
"""

from communications.models import WhatsAppContact, WhatsAppContactStatus, WhatsAppMessageLog
from onboarding.queries import count_pending_intakes


def count_whatsapp_contacts():
    return WhatsAppContact.objects.count()


def count_messages_logged():
    return WhatsAppMessageLog.objects.count()


def build_communications_headline_metrics(*, today):
    return {
        'pending_intakes': count_pending_intakes(),
        'whatsapp_contacts': count_whatsapp_contacts(),
        'messages_logged': count_messages_logged(),
    }


def get_unlinked_whatsapp_contacts(*, limit=8):
    return WhatsAppContact.objects.filter(
        status=WhatsAppContactStatus.NEW,
        linked_student__isnull=True,
    ).order_by('display_name', 'phone')[:limit]
