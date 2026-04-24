"""
ARQUIVO: persistencia e leitura da politica de aprovacao de WOD por box.

POR QUE ELE EXISTE:
- tira a politica do fallback puro de settings e coloca uma fonte real por unidade operacional.
"""

from django.conf import settings

from shared_support.cascade.ownership import resolve_actor_box_id

from .models import WorkoutApprovalPolicySetting

VALID_WOD_APPROVAL_POLICIES = ('strict', 'trusted_template', 'coach_autonomy')


def normalize_workout_approval_policy(policy):
    normalized = (policy or 'strict').strip()
    return normalized if normalized in VALID_WOD_APPROVAL_POLICIES else 'strict'


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


def get_or_create_workout_approval_policy_setting(*, actor=None, preferred_box_id=None):
    box_id = preferred_box_id if preferred_box_id not in (None, '') else resolve_actor_box_id(actor)
    if box_id in (None, ''):
        return None
    setting, _ = WorkoutApprovalPolicySetting.objects.get_or_create(
        box_id=box_id,
        defaults={
            'approval_policy': normalize_workout_approval_policy(getattr(settings, 'WOD_APPROVAL_POLICY', 'strict')),
            'updated_by': actor,
        },
    )
    return setting


def update_workout_approval_policy_setting(*, actor, approval_policy, preferred_box_id=None):
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
    'normalize_workout_approval_policy',
    'resolve_workout_approval_policy',
    'update_workout_approval_policy_setting',
]
