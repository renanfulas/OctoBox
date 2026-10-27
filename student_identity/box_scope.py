"""Helpers for scoping shared student onboarding records to the active Box."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import connection
from django.db.models import Q


@dataclass(frozen=True)
class StudentIdentityBoxScope:
    """Canonical Box metadata and a safe predicate for legacy shared rows."""

    box: object | None
    box_root_slug: str
    predicate: Q


def get_student_identity_box_scope(request=None) -> StudentIdentityBoxScope:
    """Return a current-Box predicate while keeping legacy slug rows readable.

    The Box FK is authoritative whenever present. A legacy slug is accepted
    only for rows whose FK is null, so a mismatched FK/slug cannot cross Box
    boundaries. Both the tenant schema name and the historical Box slug are
    recognized during the migration period.
    """
    from control.models import Box
    from shared_support.box_runtime import get_box_runtime_slug

    box = getattr(request, 'tenant', None) if request is not None else None
    if box is None:
        box = getattr(connection, 'tenant', None)

    current_schema = getattr(connection, 'schema_name', None)
    if current_schema and current_schema not in {'public', 'control'}:
        # Resolve from the active DB schema first: request metadata must not
        # broaden a query if it ever disagrees with the connection tenant.
        box = Box.objects.filter(schema_name=current_schema).first() or box

    if box is None or not getattr(box, 'pk', None):
        runtime_slug = get_box_runtime_slug()
        box = (
            Box.objects.filter(schema_name=runtime_slug).first()
            or Box.objects.filter(slug=runtime_slug).first()
        )

    if box is not None and getattr(box, 'pk', None):
        return _scope_for_box(box)

    # On single-box legacy/dev setups without a control.Box row, keep access
    # limited to unbound records for the configured runtime identifier.
    runtime_slug = get_box_runtime_slug()
    return StudentIdentityBoxScope(
        box=None,
        box_root_slug=runtime_slug,
        predicate=Q(box__isnull=True, box_root_slug=runtime_slug),
    )


def get_student_identity_box_scope_for_root(box_root_slug: str) -> StudentIdentityBoxScope:
    """Resolve an explicit schema/slug reference without trusting the text alone."""
    from control.models import Box
    from shared_support.box_runtime import get_box_runtime_slug

    reference = (box_root_slug or '').strip()
    if not reference:
        runtime_slug = get_box_runtime_slug()
        return StudentIdentityBoxScope(
            box=None,
            box_root_slug=runtime_slug,
            predicate=Q(box__isnull=True, box_root_slug=runtime_slug),
        )

    active_box = getattr(connection, 'tenant', None)
    active_aliases = {
        value for value in (getattr(active_box, 'schema_name', ''), getattr(active_box, 'slug', '')) if value
    }
    if active_box is not None and getattr(active_box, 'pk', None) and reference in active_aliases:
        return _scope_for_box(active_box)

    box = (
        Box.objects.filter(schema_name=reference).first()
        or Box.objects.filter(slug=reference).first()
    )
    if box is not None:
        return _scope_for_box(box)

    return StudentIdentityBoxScope(
        box=None,
        box_root_slug=reference,
        predicate=Q(box__isnull=True, box_root_slug=reference),
    )


def get_student_identity_box_scope_for_box_id(box_id: int | None) -> StudentIdentityBoxScope | None:
    """Resolve a persisted Box FK to the same canonical scope used by aliases."""
    if not box_id:
        return None
    from control.models import Box

    box = Box.objects.filter(pk=box_id).first()
    return _scope_for_box(box) if box is not None else None


def student_identity_box_references_match(
    *,
    box_id: int | None,
    box_root_slug: str,
    target_box_root_slug: str,
) -> bool:
    """Compare a Box FK/legacy alias pair against another Box reference."""
    source_scope = get_student_identity_box_scope_for_box_id(box_id)
    if source_scope is None:
        source_scope = get_student_identity_box_scope_for_root(box_root_slug)
    target_scope = get_student_identity_box_scope_for_root(target_box_root_slug)
    if source_scope.box is not None and target_scope.box is not None:
        return source_scope.box.pk == target_scope.box.pk
    if source_scope.box is not None:
        return target_box_root_slug in {source_scope.box.schema_name, source_scope.box.slug}
    if target_scope.box is not None:
        return box_root_slug in {target_scope.box.schema_name, target_scope.box.slug}
    return (box_root_slug or '') == (target_box_root_slug or '')


def _scope_for_box(box) -> StudentIdentityBoxScope:
    from shared_support.box_runtime import get_box_runtime_slug

    aliases = {value for value in (getattr(box, 'schema_name', ''), getattr(box, 'slug', '')) if value}
    canonical_slug = getattr(box, 'schema_name', '') or get_box_runtime_slug()
    return StudentIdentityBoxScope(
        box=box,
        box_root_slug=canonical_slug,
        predicate=Q(box_id=box.pk) | Q(box__isnull=True, box_root_slug__in=aliases),
    )
