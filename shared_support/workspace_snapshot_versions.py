"""
ARQUIVO: versoes canonicas e leves para snapshots de workspace.

POR QUE ELE EXISTE:
- oferece uma noção pequena e consistente de versao para workspaces operacionais.
- prepara degradacao de SSE para polling/version sem exigir barramento novo agora.

PONTOS CRITICOS:
- a versao precisa ser barata de montar.
- ela nao substitui locks nem eventos; ela ajuda a decidir se vale refrescar.
"""

from __future__ import annotations

from datetime import date, datetime


DEFAULT_VERSION_FIELDS = (
    'updated_at',
    'created_at',
    'resolved_at',
    'suggested_at',
    'scheduled_at',
    'last_outbound_at',
    'last_inbound_at',
    'captured_at',
    'due_date',
)


def serialize_workspace_version_value(value) -> str:
    if not value:
        return ''
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _extract_marker_from_item(item):
    if item is None:
        return None
    if isinstance(item, dict):
        for field_name in DEFAULT_VERSION_FIELDS:
            value = item.get(field_name)
            if value:
                return value
        return None
    for field_name in DEFAULT_VERSION_FIELDS:
        value = getattr(item, field_name, None)
        if value:
            return value
    return None


def build_workspace_snapshot_version(*parts) -> str:
    serialized_parts = []

    for part in parts:
        if not part:
            continue
        key = str(part.get('key') or 'part')
        count = part.get('count')
        items = list(part.get('items') or [])
        marker = part.get('marker')

        if count is None:
            count = len(items)

        if marker is None and items:
            markers = [_extract_marker_from_item(item) for item in items]
            markers = [value for value in markers if value is not None]
            if markers:
                marker = max(markers)

        serialized_parts.append(
            f'{key}:{count}@{serialize_workspace_version_value(marker)}'
        )

    return '|'.join(serialized_parts)


__all__ = [
    'build_workspace_snapshot_version',
    'serialize_workspace_version_value',
]
