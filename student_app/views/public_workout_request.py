"""Adaptador HTTP compartilhado pelos endpoints autenticados da Curva."""

import json


def json_payload(request, *, max_bytes=16384):
    if len(request.body) > max_bytes:
        return None
    try:
        value = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None
