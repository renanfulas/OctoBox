"""Fachada publica das rotinas de communications usadas pelo catalogo."""

from communications.services import (
    build_message_body,
    ensure_whatsapp_contact,
    normalize_payment_status,
    register_operational_message,
)

__all__ = [
    'build_message_body',
    'ensure_whatsapp_contact',
    'normalize_payment_status',
    'register_operational_message',
]