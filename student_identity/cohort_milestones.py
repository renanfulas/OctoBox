"""Tenant-local persistence for the versioned activation cohort facts."""

from __future__ import annotations

import hashlib
import json

from django.db import connection
from django.utils import timezone
from django_tenants.utils import schema_context

from control.tenant_write_fence import tenant_write_guard


COHORT_START_MILESTONES = {'invite_created', 'link_created'}
COHORT_ACTIVATION_MILESTONES = {'app_entry_completed'}
COHORT_MILESTONES = COHORT_START_MILESTONES | COHORT_ACTIVATION_MILESTONES


def _milestone_keys(*, journey: str, event: str, target_model: str, target_id: str, metadata: dict):
    identity_id = metadata.get('identity_id')
    invitation_id = metadata.get('invitation_id')
    invite_link_id = metadata.get('box_invite_link_id')
    if journey == 'mass_box_invite':
        invite_link_id = invite_link_id or (target_id if 'StudentBoxInviteLink' in target_model else '')
        cohort_kind, cohort_key = 'invite_link', str(invite_link_id or '')
    else:
        invitation_id = invitation_id or (target_id if 'StudentAppInvitation' in target_model else '')
        cohort_kind = 'invitation' if invitation_id else 'identity'
        cohort_key = str(invitation_id or identity_id or '')

    if identity_id:
        subject_kind, subject_key = 'identity', str(identity_id)
    elif invitation_id:
        subject_kind, subject_key = 'invitation', str(invitation_id)
    elif invite_link_id:
        subject_kind, subject_key = 'invite_link', str(invite_link_id)
    elif event == 'invite_created' and target_id:
        subject_kind, subject_key = 'invitation', str(target_id)
    elif event == 'link_created' and target_id:
        subject_kind, subject_key = 'invite_link', str(target_id)
    else:
        subject_kind, subject_key = '', ''

    if not subject_key or not cohort_key:
        return None
    return subject_kind, subject_key, cohort_kind, cohort_key, int(identity_id) if identity_id else None


def persist_onboarding_milestone(*, journey: str, event: str, target_model: str, target_id: str, metadata: dict):
    if event not in COHORT_MILESTONES:
        return None
    keys = _milestone_keys(
        journey=journey,
        event=event,
        target_model=target_model,
        target_id=target_id,
        metadata=metadata,
    )
    if keys is None:
        return None

    subject_kind, subject_key, cohort_kind, cohort_key, identity_id = keys
    occurred_at = timezone.now()
    local_timezone = timezone.get_current_timezone()
    idempotency_payload = [1, journey, event, subject_kind, subject_key, cohort_kind, cohort_key]
    idempotency_key = hashlib.sha256(
        json.dumps(idempotency_payload, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    ).hexdigest()

    def write_in_tenant(schema_name):
        from student_app.models import StudentJourneyMilestone

        with tenant_write_guard(schema_name):
            return StudentJourneyMilestone.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults={
                    'journey': journey,
                    'milestone': event,
                    'subject_kind': subject_kind,
                    'subject_key': subject_key,
                    'cohort_kind': cohort_kind,
                    'cohort_key': cohort_key,
                    'identity_id': identity_id,
                    'occurred_at': occurred_at,
                    'timezone_name': getattr(local_timezone, 'key', None) or str(local_timezone),
                    'contract_version': 1,
                },
            )[0]

    current_schema = getattr(connection, 'schema_name', 'public')
    box_root_slug = str(metadata.get('box_root_slug') or '').strip()
    if current_schema and current_schema != 'public':
        if box_root_slug and box_root_slug != current_schema:
            from control.models import Box

            aliases = Box.objects.filter(schema_name=current_schema).values_list('schema_name', 'slug').first()
            if aliases is None or box_root_slug not in aliases:
                raise RuntimeError('Milestone de onboarding tentou gravar em tenant divergente.')
        return write_in_tenant(current_schema)

    if not box_root_slug:
        return None
    from control.models import Box

    box = (
        Box.objects.filter(schema_name=box_root_slug, status=Box.Status.ACTIVE).only('schema_name').first()
        or Box.objects.filter(slug=box_root_slug, status=Box.Status.ACTIVE).only('schema_name').first()
    )
    if box is None:
        return None
    with schema_context(box.schema_name):
        return write_in_tenant(box.schema_name)


def record_authenticated_student_return(*, identity_id: int | None, occurred_at=None, activity_kind: str):
    from student_identity.domain.cohort_contracts import RETURN_ACTIVITY_KINDS

    if not identity_id or activity_kind not in RETURN_ACTIVITY_KINDS:
        return None
    occurred_at = occurred_at or timezone.now()
    local_timezone = timezone.get_current_timezone()
    timezone_name = getattr(local_timezone, 'key', None) or str(local_timezone)
    local_day = occurred_at.astimezone(local_timezone).date().isoformat()
    identity_key = str(int(identity_id))
    payload = [1, 'authenticated_return', identity_key, local_day]
    idempotency_key = hashlib.sha256(
        json.dumps(payload, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    ).hexdigest()
    from student_app.models import StudentJourneyMilestone

    schema_name = getattr(connection, 'schema_name', 'public')
    if not schema_name or schema_name == 'public':
        return None
    with tenant_write_guard(schema_name):
        return StudentJourneyMilestone.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                'journey': '',
                'milestone': 'authenticated_return',
                'subject_kind': 'identity',
                'subject_key': identity_key,
                'cohort_kind': 'identity',
                'cohort_key': identity_key,
                'identity_id': int(identity_id),
                'occurred_at': occurred_at,
                'timezone_name': timezone_name,
                'contract_version': 1,
            },
        )[0]


def record_student_first_checkin(*, student_id: int | None, occurred_at=None):
    if not student_id:
        return None
    schema_name = getattr(connection, 'schema_name', 'public')
    if not schema_name or schema_name == 'public':
        return None
    occurred_at = occurred_at or timezone.now()
    local_timezone = timezone.get_current_timezone()
    timezone_name = getattr(local_timezone, 'key', None) or str(local_timezone)
    student_key = str(int(student_id))
    payload = [1, 'first_checkin', schema_name, student_key]
    idempotency_key = hashlib.sha256(
        json.dumps(payload, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    ).hexdigest()
    from student_app.models import StudentJourneyMilestone

    with tenant_write_guard(schema_name):
        return StudentJourneyMilestone.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                'journey': 'attendance',
                'milestone': 'first_checkin',
                'subject_kind': 'student',
                'subject_key': student_key,
                'cohort_kind': 'box_student',
                'cohort_key': student_key,
                'occurred_at': occurred_at,
                'timezone_name': timezone_name,
                'contract_version': 1,
            },
        )[0]


__all__ = [
    'persist_onboarding_milestone',
    'record_authenticated_student_return',
    'record_student_first_checkin',
]
