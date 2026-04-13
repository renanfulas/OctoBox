"""
ARQUIVO: contratos leves da cascata por unidade.

POR QUE ELE EXISTE:
- padroniza a forma de representar intencao e resolucao antes da cascata completa existir.
- reduz o custo de migrar fluxos diretos para um owner hub real no futuro.

PONTOS CRITICOS:
- este modulo nao deve criar hop extra no runtime.
- os contratos aqui precisam ser baratos de montar e seguros para serializar em metadata.
"""

from __future__ import annotations

from uuid import uuid4

from django.utils import timezone


CASCADE_INTENT_FIELDS = (
    'intent_id',
    'box_id',
    'owner_user_id',
    'requested_by_user_id',
    'requested_by_role',
    'subject_type',
    'subject_id',
    'action_kind',
    'channel',
    'surface',
    'requested_at',
)

CASCADE_RESOLUTION_FIELDS = (
    'intent_id',
    'status',
    'stage_before',
    'stage_after',
    'ownership_scope',
    'canonical_event_id',
    'resolved_at',
)


def _serialize_datetime(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def build_cascade_intent(
    *,
    box_id=None,
    owner_user_id=None,
    requested_by_user_id=None,
    requested_by_role='',
    subject_type='',
    subject_id=None,
    action_kind='',
    channel='',
    surface='',
    requested_at=None,
    intent_id='',
):
    requested_at_value = requested_at or timezone.now()
    return {
        'intent_id': intent_id or uuid4().hex,
        'box_id': box_id,
        'owner_user_id': owner_user_id,
        'requested_by_user_id': requested_by_user_id,
        'requested_by_role': requested_by_role,
        'subject_type': subject_type,
        'subject_id': str(subject_id) if subject_id is not None else '',
        'action_kind': action_kind,
        'channel': channel,
        'surface': surface,
        'requested_at': _serialize_datetime(requested_at_value),
    }


def build_cascade_resolution(
    *,
    intent_id,
    status='accepted',
    stage_before='',
    stage_after='',
    ownership_scope='',
    canonical_event_id='',
    resolved_at=None,
):
    resolved_at_value = resolved_at or timezone.now()
    return {
        'intent_id': intent_id,
        'status': status,
        'stage_before': stage_before,
        'stage_after': stage_after,
        'ownership_scope': ownership_scope,
        'canonical_event_id': str(canonical_event_id) if canonical_event_id else '',
        'resolved_at': _serialize_datetime(resolved_at_value),
    }


def merge_cascade_metadata(metadata=None, *, intent=None, resolution=None):
    merged = dict(metadata or {})
    if intent:
        for field_name in CASCADE_INTENT_FIELDS:
            if field_name in intent:
                merged[field_name] = intent[field_name]
    if resolution:
        for field_name in CASCADE_RESOLUTION_FIELDS:
            if field_name in resolution:
                merged[field_name] = resolution[field_name]
    return merged


__all__ = [
    'CASCADE_INTENT_FIELDS',
    'CASCADE_RESOLUTION_FIELDS',
    'build_cascade_intent',
    'build_cascade_resolution',
    'merge_cascade_metadata',
]
