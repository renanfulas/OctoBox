from __future__ import annotations

import threading
import logging

from django.conf import settings
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from auditing.models import AuditEvent
from control.tenant_write_fence import TenantWritesFrozen, tenant_write_guard

logger = logging.getLogger(__name__)


def build_student_onboarding_event_action(*, journey: str, event: str) -> str:
    return f'student_onboarding.{journey}.{event}'


def record_student_onboarding_event(
    *,
    journey: str,
    event: str,
    target_model: str = '',
    target_id: str = '',
    target_label: str = '',
    description: str = '',
    actor=None,
    actor_role: str = '',
    metadata: dict | None = None,
):
    payload = {
        'journey': journey,
        **(metadata or {}),
    }
    kwargs = dict(
        actor=actor,
        actor_role=actor_role,
        action=build_student_onboarding_event_action(journey=journey, event=event),
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        description=description,
        metadata=payload,
    )
    tenant_schema = getattr(connection, 'schema_name', '')
    if not tenant_schema or tenant_schema == get_public_schema_name():
        box_root_slug = str(payload.get('box_root_slug') or '').strip()
        if box_root_slug:
            from control.models import Box

            box = (
                Box.objects.filter(schema_name=box_root_slug, status=Box.Status.ACTIVE).first()
                or Box.objects.filter(slug=box_root_slug, status=Box.Status.ACTIVE).first()
            )
            tenant_schema = box.schema_name if box is not None else ''

    if not tenant_schema or tenant_schema == get_public_schema_name():
        logger.info('student_onboarding_audit_skipped_unattributed')
        return None

    def _write():
        with schema_context(tenant_schema):
            with tenant_write_guard(tenant_schema):
                from student_identity.cohort_milestones import persist_onboarding_milestone
                persist_onboarding_milestone(
                    journey=journey,
                    event=event,
                    target_model=target_model,
                    target_id=target_id,
                    metadata=payload,
                )
                return AuditEvent.objects.create(**kwargs)

    def _write_async():
        try:
            _write()
        except TenantWritesFrozen:
            logger.info('student_onboarding_audit_skipped_tenant_frozen')

    if getattr(settings, 'STUDENT_AUDIT_ASYNC', False):
        transaction.on_commit(lambda: threading.Thread(target=_write_async, daemon=True).start())
        return None
    return _write()
