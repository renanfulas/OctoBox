"""Tenant context helpers for short-lived Redis event streams."""

from __future__ import annotations

import re

from django.db import connection


_BOX_SCHEMA_RE = re.compile(r"^box_[a-z0-9_-]{1,59}$")


def is_box_event_schema(schema_name: object) -> bool:
    """Accept only canonical schema names produced for an OctoBox tenant."""

    return isinstance(schema_name, str) and _BOX_SCHEMA_RE.fullmatch(schema_name) is not None


def current_event_tenant_schema() -> str | None:
    """Return the active tenant schema, never a shared/public namespace."""

    schema_name = getattr(connection, "schema_name", "")
    return schema_name if is_box_event_schema(schema_name) else None


__all__ = ["current_event_tenant_schema", "is_box_event_schema"]
