"""
ARQUIVO: utilitarios de inspecao de payload HTML publicado.

POR QUE ELE EXISTE:
- padroniza a medicao de paginas publicadas com a mesma regua usada localmente.
- evita scripts soltos reimplementando parse de headers, html e current_page_behavior.

O QUE ESTE ARQUIVO FAZ:
1. extrai o bloco JSON de `current_page_behavior` do HTML renderizado.
2. resume tamanhos do HTML e do payload embutido.
3. expõe metricas de `directory_search` e `performance_timing` para comparacao local x website.

PONTOS CRITICOS:
- depende do contrato de `json_script:"current-page-behavior"` no template base.
- deve falhar de forma segura quando a pagina nao tiver payload embutido.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any


CURRENT_PAGE_BEHAVIOR_ID = "current-page-behavior"

_JSON_SCRIPT_RE = re.compile(
    r'<script[^>]*id=["\'](?P<id>[^"\']+)["\'][^>]*type=["\']application/json["\'][^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_json_script_text(html: str, *, element_id: str = CURRENT_PAGE_BEHAVIOR_ID) -> str | None:
    for match in _JSON_SCRIPT_RE.finditer(html):
        if match.group("id") != element_id:
            continue
        return html_lib.unescape(match.group("body").strip())
    return None


def extract_current_page_behavior(html: str) -> dict[str, Any]:
    payload = extract_json_script_text(html, element_id=CURRENT_PAGE_BEHAVIOR_ID)
    if not payload:
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _pick_header(headers: dict[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def _pick_timing_value(performance_timing: dict[str, Any], *names: str) -> Any:
    if not isinstance(performance_timing, dict):
        return None
    for name in names:
        if name in performance_timing:
            return performance_timing.get(name)
    return None


def summarize_published_html_probe(
    *,
    url: str,
    status_code: int,
    html: str,
    headers: dict[str, str],
    request_elapsed_ms: float,
    encoded_body_bytes: int | None = None,
) -> dict[str, Any]:
    current_page_behavior_text = extract_json_script_text(html)
    current_page_behavior = extract_current_page_behavior(html)
    directory_search = current_page_behavior.get("directory_search", {})
    performance_timing = current_page_behavior.get("performance_timing", {})

    summary = {
        "url": url,
        "status_code": status_code,
        "request_elapsed_ms": round(float(request_elapsed_ms), 2),
        "html_bytes": len(html.encode("utf-8")),
        "encoded_body_bytes": encoded_body_bytes,
        "headers": {
            "content_type": _pick_header(headers, "Content-Type"),
            "content_encoding": _pick_header(headers, "Content-Encoding"),
            "cache_control": _pick_header(headers, "Cache-Control"),
            "vary": _pick_header(headers, "Vary"),
            "etag": _pick_header(headers, "ETag"),
            "last_modified": _pick_header(headers, "Last-Modified"),
            "content_length": _pick_header(headers, "Content-Length"),
            "transfer_encoding": _pick_header(headers, "Transfer-Encoding"),
        },
        "current_page_behavior_bytes": len(current_page_behavior_text.encode("utf-8"))
        if current_page_behavior_text
        else 0,
        "current_page_behavior_present": bool(current_page_behavior_text),
        "directory_search_bytes": len(json.dumps(directory_search, ensure_ascii=False).encode("utf-8"))
        if isinstance(directory_search, dict)
        else 0,
        "directory_search_index_entries": len(directory_search.get("index", []))
        if isinstance(directory_search, dict)
        else 0,
        "directory_search_total": directory_search.get("total")
        if isinstance(directory_search, dict)
        else None,
        "directory_search_has_next": directory_search.get("has_next")
        if isinstance(directory_search, dict)
        else None,
        "listing_snapshot_ms": _pick_timing_value(
            performance_timing,
            "listing_snapshot_ms",
            "listing_duration_ms",
        ),
        "support_snapshot_ms": _pick_timing_value(
            performance_timing,
            "support_snapshot_ms",
            "support_duration_ms",
        ),
        "view_total_ms": _pick_timing_value(
            performance_timing,
            "view_total_ms",
            "total_view_duration_ms",
        ),
    }
    return summary
