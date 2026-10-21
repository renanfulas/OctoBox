"""Batch lookup for student-facing movement references.

SmartPlan slugs use underscores while older MovementLibrary rows may use
hyphens. Resolve that legacy spelling at the read boundary without changing
the canonical slug used for videos, RM records, or workout data.
"""

from __future__ import annotations

from student_app.models import MovementLibrary


def lookup_movement_reference_urls(movement_slugs):
    requested_slugs = {str(slug).strip() for slug in movement_slugs if str(slug).strip()}
    if not requested_slugs:
        return {}

    lookup_slugs = requested_slugs | {
        slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        for slug in requested_slugs
    }
    library_urls = dict(
        MovementLibrary.objects.filter(slug__in=lookup_slugs)
        .values_list('slug', 'reference_url')
    )
    resolved = {}
    for slug in requested_slugs:
        url = library_urls.get(slug)
        if not url:
            alias = slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
            url = library_urls.get(alias, '')
        resolved[slug] = url or ''
    return resolved


def lookup_movement_demo_video_urls(movement_slugs):
    requested_slugs = {str(slug).strip() for slug in movement_slugs if str(slug).strip()}
    if not requested_slugs:
        return {}
    lookup_slugs = requested_slugs | {
        slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        for slug in requested_slugs
    }
    library_urls = dict(
        MovementLibrary.objects.filter(slug__in=lookup_slugs)
        .values_list('slug', 'demo_video_url')
    )
    resolved = {}
    for slug in requested_slugs:
        alias = slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        resolved[slug] = library_urls.get(slug) or library_urls.get(alias) or ''
    return resolved


def lookup_movement_video_metadata(movement_slugs):
    """Batch both student-facing links in one catalog query."""
    requested_slugs = {str(slug).strip() for slug in movement_slugs if str(slug).strip()}
    if not requested_slugs:
        return {}
    lookup_slugs = requested_slugs | {
        slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        for slug in requested_slugs
    }
    rows = {
        slug: {'reference_url': reference_url or '', 'demo_video_url': demo_video_url or ''}
        for slug, reference_url, demo_video_url in MovementLibrary.objects.filter(slug__in=lookup_slugs)
        .values_list('slug', 'reference_url', 'demo_video_url')
    }
    result = {}
    for slug in requested_slugs:
        alias = slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        result[slug] = rows.get(slug) or rows.get(alias) or {
            'reference_url': '',
            'demo_video_url': '',
        }
    return result


def lookup_movement_catalog_status(movement_slugs):
    requested_slugs = {str(slug).strip() for slug in movement_slugs if str(slug).strip()}
    if not requested_slugs:
        return {}
    lookup_slugs = requested_slugs | {
        slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        for slug in requested_slugs
    }
    rows = dict(MovementLibrary.objects.filter(slug__in=lookup_slugs).values_list('slug', 'demo_video_url'))
    result = {}
    for slug in requested_slugs:
        alias = slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
        matched_slug = slug if slug in rows else alias if alias in rows else None
        result[slug] = {
            'is_registered': matched_slug is not None,
            'demo_video_url': rows.get(matched_slug, '') if matched_slug else '',
        }
    return result


__all__ = [
    'lookup_movement_reference_urls',
    'lookup_movement_demo_video_urls',
    'lookup_movement_video_metadata',
    'lookup_movement_catalog_status',
]
