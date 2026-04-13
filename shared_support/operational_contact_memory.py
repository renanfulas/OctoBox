"""
ARQUIVO: contrato compartilhado da memoria curta de contato operacional.

POR QUE ELE EXISTE:
- evita espalhar strings magicas de historico, stage e ownership por varias telas.
- prepara a migracao futura de AuditEvent para um read model dedicado.

O QUE ESTE ARQUIVO FAZ:
1. define as acoes canonicas de contato operacional.
2. define stage, ownership e janelas de cooldown/historico.
3. fornece helpers pequenos para metadata e leitura.
"""

from __future__ import annotations

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION

CONTACT_HISTORY_LOOKBACK_DAYS = 15
CONTACT_COOLDOWN_DAYS = 3

CONTACT_STAGE_UNREACHED = 'unreached'
CONTACT_STAGE_FIRST_TOUCH_OPENED = 'first_touch_opened'
CONTACT_STAGE_FOLLOW_UP_ACTIVE = 'follow_up_active'
CONTACT_STAGE_RESOLVED = 'resolved'

CONTACT_OWNERSHIP_SHARED = 'shared_reception_manager'
CONTACT_OWNERSHIP_MANAGER_OWNER = 'manager_owner'

MANAGER_INTAKE_FIRST_TOUCH_ACTION = 'manager.intake.first_touch_opened'
MANAGER_INTAKE_FOLLOW_UP_ACTION = 'manager.intake.follow_up_opened'
MANAGER_FINANCE_WHATSAPP_ACTION = 'manager.finance.whatsapp_opened'
RECEPTION_FINANCE_WHATSAPP_ACTION = 'reception.finance.whatsapp_opened'
OWNER_FINANCE_WHATSAPP_ACTION = 'owner.finance.whatsapp_opened'

INTAKE_CONTACT_ACTIONS = {
    MANAGER_INTAKE_FIRST_TOUCH_ACTION,
    MANAGER_INTAKE_FOLLOW_UP_ACTION,
}

FINANCE_CONTACT_ACTIONS = {
    MANAGER_FINANCE_WHATSAPP_ACTION,
    RECEPTION_FINANCE_WHATSAPP_ACTION,
    OWNER_FINANCE_WHATSAPP_ACTION,
}

CONTACT_MEMORY_ACTIONS = INTAKE_CONTACT_ACTIONS | FINANCE_CONTACT_ACTIONS

TEAM_CONTACT_ROLE_SLUGS = {
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_RECEPTION,
}

ROLE_LABELS = {
    ROLE_MANAGER: 'Gerencia',
    ROLE_OWNER: 'Owner',
    ROLE_RECEPTION: 'Recepcao',
}

ACTION_LABELS = {
    MANAGER_INTAKE_FIRST_TOUCH_ACTION: 'WhatsApp inicial enviado',
    MANAGER_INTAKE_FOLLOW_UP_ACTION: 'Follow-up retomado',
    MANAGER_FINANCE_WHATSAPP_ACTION: 'Cobranca no WhatsApp',
    RECEPTION_FINANCE_WHATSAPP_ACTION: 'Cobranca no WhatsApp',
    OWNER_FINANCE_WHATSAPP_ACTION: 'Cobranca no WhatsApp',
}

SURFACE_LABELS = {
    'intake': 'Entradas',
    'finance': 'Cobranca',
}


def build_contact_subject_key(subject_type: str, subject_id) -> str:
    return f'{subject_type}:{subject_id}'


def build_contact_memory_metadata(
    *,
    board_key: str,
    channel: str,
    subject_type: str,
    subject_id,
    subject_label: str,
    student_id=None,
    payment_id=None,
    intake_id=None,
    stage_before: str,
    stage_after: str,
    ownership_scope: str,
    cooldown_until: str = '',
    is_first_touch: bool = False,
):
    return {
        'board_key': board_key,
        'channel': channel,
        'subject_type': subject_type,
        'subject_id': str(subject_id),
        'subject_label': subject_label,
        'student_id': student_id,
        'payment_id': payment_id,
        'intake_id': intake_id,
        'stage_before': stage_before,
        'stage_after': stage_after,
        'ownership_scope': ownership_scope,
        'cooldown_until': cooldown_until,
        'is_first_touch': bool(is_first_touch),
    }


def is_contact_memory_action(action: str) -> bool:
    return action in CONTACT_MEMORY_ACTIONS


def is_finance_contact_action(action: str) -> bool:
    return action in FINANCE_CONTACT_ACTIONS


def is_intake_contact_action(action: str) -> bool:
    return action in INTAKE_CONTACT_ACTIONS


__all__ = [
    'ACTION_LABELS',
    'CONTACT_COOLDOWN_DAYS',
    'CONTACT_HISTORY_LOOKBACK_DAYS',
    'CONTACT_MEMORY_ACTIONS',
    'CONTACT_OWNERSHIP_MANAGER_OWNER',
    'CONTACT_OWNERSHIP_SHARED',
    'CONTACT_STAGE_FIRST_TOUCH_OPENED',
    'CONTACT_STAGE_FOLLOW_UP_ACTIVE',
    'CONTACT_STAGE_RESOLVED',
    'CONTACT_STAGE_UNREACHED',
    'FINANCE_CONTACT_ACTIONS',
    'INTAKE_CONTACT_ACTIONS',
    'MANAGER_FINANCE_WHATSAPP_ACTION',
    'MANAGER_INTAKE_FIRST_TOUCH_ACTION',
    'MANAGER_INTAKE_FOLLOW_UP_ACTION',
    'OWNER_FINANCE_WHATSAPP_ACTION',
    'RECEPTION_FINANCE_WHATSAPP_ACTION',
    'ROLE_LABELS',
    'SURFACE_LABELS',
    'TEAM_CONTACT_ROLE_SLUGS',
    'build_contact_memory_metadata',
    'build_contact_subject_key',
    'is_contact_memory_action',
    'is_finance_contact_action',
    'is_intake_contact_action',
]
