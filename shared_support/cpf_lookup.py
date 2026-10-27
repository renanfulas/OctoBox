"""Tenant-scoped activation gate for exact CPF lookup by blind index."""

from django.conf import settings
from django.db import connection


def cpf_lookup_index_is_ready() -> bool:
    """Return whether the current tenant has completed the CPF-index rollout."""

    schema_name = getattr(connection, "schema_name", "")
    if not schema_name.startswith("box_"):
        return False
    if getattr(settings, "CPF_LOOKUP_INDEX_READY", False):
        return True
    ready_schemas = getattr(settings, "CPF_LOOKUP_INDEX_READY_BOXES", ())
    return schema_name in ready_schemas


__all__ = ["cpf_lookup_index_is_ready"]
