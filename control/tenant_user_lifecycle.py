"""Cross-schema user deletion while respecting tenant write fences."""

from __future__ import annotations

import logging
from contextlib import ExitStack

from django.conf import settings
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context

from control.tenant_write_fence import tenant_write_exclusive

logger = logging.getLogger('control.services')
User = get_user_model()


def _tenant_user_fk_fields():
    """Discover tenant models with reverse FKs to User at runtime."""
    tenant_labels = {entry.split('.')[0] for entry in settings.TENANT_APPS}
    return [
        (rel.related_model, rel.field.name, rel.field.null)
        for rel in User._meta.get_fields()
        if rel.auto_created and not rel.concrete
        and rel.related_model._meta.app_label in tenant_labels
    ]


def delete_user_safely(user) -> None:
    """Clean tenant references before deleting a shared user.

    All affected Boxes are locked before the first mutation, preventing a
    frozen tenant from leaving the user only partially cleaned up.
    """
    from control.models import Box, Membership

    username = getattr(user, 'username', user.pk)
    with schema_context(get_public_schema_name()):
        fk_fields = _tenant_user_fk_fields()
        box_ids = Membership.objects.filter(user=user).values_list('box_id', flat=True).distinct()
        boxes = list(Box.objects.filter(pk__in=box_ids).order_by('schema_name'))
        with ExitStack() as locks:
            for box in boxes:
                locks.enter_context(tenant_write_exclusive(box.schema_name))
            for box in boxes:
                with schema_context(box.schema_name):
                    for model, field_name, nullable in fk_fields:
                        qs = model.objects.filter(**{field_name: user})
                        changed = qs.update(**{field_name: None}) if nullable else qs.delete()[0]
                        if changed:
                            logger.info(
                                'delete_user_safely: tenant references cleaned model=%s field=%s count=%s box=%s user=%s',
                                model.__name__, field_name, changed, box.schema_name, username,
                            )
            user.delete()
    logger.info('delete_user_safely: user=%s deletado.', username)


__all__ = ['delete_user_safely']
