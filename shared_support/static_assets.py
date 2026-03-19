"""Helpers para expandir manifestos CSS em folhas runtime versionaveis."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings


_CSS_IMPORT_RE = re.compile(r'@import\s+url\(["\'](?P<path>[^"\']+\.css)["\']\)')


def resolve_runtime_css_paths(stylesheet_paths):
    resolved_paths = []
    seen_paths = set()

    for stylesheet_path in stylesheet_paths or []:
        for runtime_path in _expand_css_manifest(_normalize_asset_path(stylesheet_path), stack=()):
            if runtime_path in seen_paths:
                continue
            seen_paths.add(runtime_path)
            resolved_paths.append(runtime_path)

    return resolved_paths


def _expand_css_manifest(stylesheet_path, *, stack):
    asset_file = settings.BASE_DIR / 'static' / stylesheet_path

    if stylesheet_path in stack or not asset_file.exists() or asset_file.suffix.lower() != '.css':
        return [stylesheet_path]

    css_text = asset_file.read_text(encoding='utf-8')
    import_paths = [match.group('path') for match in _CSS_IMPORT_RE.finditer(css_text)]
    if not import_paths:
        return [stylesheet_path]

    expanded_paths = []
    for import_path in import_paths:
        child_path = _resolve_import_path(stylesheet_path, import_path)
        expanded_paths.extend(_expand_css_manifest(child_path, stack=(*stack, stylesheet_path)))
    return expanded_paths


def _normalize_asset_path(asset_path):
    return str(Path(asset_path).as_posix())


def _resolve_import_path(parent_asset_path, import_path):
    parent_dir = Path(parent_asset_path).parent
    static_root = (settings.BASE_DIR / 'static').resolve()
    return (static_root / parent_dir / import_path).resolve().relative_to(static_root).as_posix()