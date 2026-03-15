"""Helpers compartilhados para leitura do estado operacional do WhatsApp."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def build_whatsapp_contact_state(contact):
    repeat_block_hours = max(0, int(getattr(settings, 'OPERATIONAL_WHATSAPP_REPEAT_BLOCK_HOURS', 24)))
    if contact is None or contact.last_outbound_at is None:
        return {
            'whatsapp_last_contact_label': 'Nenhum contato operacional recente registrado.',
            'whatsapp_next_available_label': '',
            'whatsapp_repeat_blocked': False,
        }

    last_outbound_at = timezone.localtime(contact.last_outbound_at)
    last_contact_label = f'Ultimo contato: {last_outbound_at:%d/%m/%Y %H:%M}.'
    if repeat_block_hours == 0:
        return {
            'whatsapp_last_contact_label': last_contact_label,
            'whatsapp_next_available_label': 'Repeticao imediata liberada nesta configuracao.',
            'whatsapp_repeat_blocked': False,
        }

    next_available_at = last_outbound_at + timedelta(hours=repeat_block_hours)
    now = timezone.localtime()
    return {
        'whatsapp_last_contact_label': last_contact_label,
        'whatsapp_next_available_label': (
            f'Novo disparo libera em {next_available_at:%d/%m/%Y %H:%M}.'
            if next_available_at > now else
            'Janela liberada para novo contato.'
        ),
        'whatsapp_repeat_blocked': next_available_at > now,
    }