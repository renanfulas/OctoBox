"""
ARQUIVO: persistencia e leitura da politica de aprovacao de WOD por box.

POR QUE ELE EXISTE:
- tira a politica do fallback puro de settings e coloca uma fonte real por unidade operacional.
"""

from django.conf import settings
from django.db import connection, transaction

from shared_support.cascade.ownership import resolve_actor_box_id

from .models import WorkoutApprovalPolicySetting

VALID_WOD_APPROVAL_POLICIES = ('strict', 'trusted_template', 'coach_autonomy')
_POLICY_ADVISORY_LOCK_NAMESPACE = 0x4F43544F


def normalize_workout_approval_policy(policy):
    normalized = (policy or 'strict').strip()
    return normalized if normalized in VALID_WOD_APPROVAL_POLICIES else 'strict'


def lock_workout_approval_policy(*, box_id):
    """Serialize policy reads-for-confirmation with create/update, including a missing row."""
    if box_id in (None, ''):
        return
    box_id = int(box_id)
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s, %s)',
                [_POLICY_ADVISORY_LOCK_NAMESPACE, box_id],
            )
    list(WorkoutApprovalPolicySetting.objects.select_for_update().filter(box_id=box_id).values_list('id', flat=True))


def resolve_workout_approval_policy(*, actor=None, session=None, preferred_box_id=None):
    direct_policy = getattr(getattr(session, 'box', None), 'wod_approval_policy', None)
    if direct_policy not in (None, ''):
        return normalize_workout_approval_policy(direct_policy)

    box_id = preferred_box_id
    if box_id in (None, ''):
        box_id = getattr(getattr(session, 'box', None), 'id', None) or getattr(session, 'box_id', None)
    if box_id in (None, ''):
        box_id = resolve_actor_box_id(actor)
    if box_id not in (None, ''):
        record = WorkoutApprovalPolicySetting.objects.filter(box_id=box_id).only('approval_policy').first()
        if record is not None:
            return record.approval_policy
    return normalize_workout_approval_policy(getattr(settings, 'WOD_APPROVAL_POLICY', 'strict'))


@transaction.atomic
def get_or_create_workout_approval_policy_setting(*, actor=None, preferred_box_id=None):
    box_id = preferred_box_id if preferred_box_id not in (None, '') else resolve_actor_box_id(actor)
    if box_id in (None, ''):
        return None
    lock_workout_approval_policy(box_id=box_id)
    setting, _ = WorkoutApprovalPolicySetting.objects.get_or_create(
        box_id=box_id,
        defaults={
            'approval_policy': normalize_workout_approval_policy(getattr(settings, 'WOD_APPROVAL_POLICY', 'strict')),
            'updated_by': actor,
        },
    )
    return setting


@transaction.atomic
def update_workout_approval_policy_setting(*, actor, approval_policy, preferred_box_id=None):
    # The nested atomic getter takes the same transaction-scoped lock; this
    # outer transaction keeps it held through the actual update.
    setting = get_or_create_workout_approval_policy_setting(actor=actor, preferred_box_id=preferred_box_id)
    if setting is None:
        return None
    setting.approval_policy = normalize_workout_approval_policy(approval_policy)
    setting.updated_by = actor
    setting.save(update_fields=['approval_policy', 'updated_by', 'updated_at'])
    return setting


__all__ = [
    'VALID_WOD_APPROVAL_POLICIES',
    'get_or_create_workout_approval_policy_setting',
    'lock_workout_approval_policy',
    'normalize_workout_approval_policy',
    'resolve_workout_approval_policy',
    'update_workout_approval_policy_setting',
]
