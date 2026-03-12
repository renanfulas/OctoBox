"""
ARQUIVO: saneamento de payloads da integracao WhatsApp.

POR QUE ELE EXISTE:
- Evita gravar payload cru demais e sem limite antes da integracao oficial.

O QUE ESTE ARQUIVO FAZ:
1. Reduz payload para tipos previsiveis.
2. Mascara chaves sensiveis conhecidas.
3. Limita profundidade, tamanho de listas e textos gravados.

PONTOS CRITICOS:
- O saneamento precisa preservar contexto suficiente para auditoria sem virar vazamento de segredo.
"""

from collections.abc import Mapping, Sequence
from typing import Any

_MAX_DEPTH = 4
_MAX_ITEMS = 25
_MAX_STRING_LENGTH = 500
_SENSITIVE_KEY_PARTS = ('token', 'secret', 'authorization', 'password', 'signature', 'jwt', 'bearer')


def _is_sensitive_key(key: str) -> bool:
    lowered_key = key.lower()
    return any(fragment in lowered_key for fragment in _SENSITIVE_KEY_PARTS)


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if depth >= _MAX_DEPTH:
        return '[truncated-depth]'
    if isinstance(value, Mapping):
        sanitized_mapping = {}
        for index, (key, nested_value) in enumerate(value.items()):
            if index >= _MAX_ITEMS:
                sanitized_mapping['__truncated__'] = True
                break
            key_as_text = str(key)
            sanitized_mapping[key_as_text] = '[redacted]' if _is_sensitive_key(key_as_text) else _sanitize_value(
                nested_value,
                depth=depth + 1,
            )
        return sanitized_mapping
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sanitized_items = [_sanitize_value(item, depth=depth + 1) for item in list(value)[:_MAX_ITEMS]]
        if len(value) > _MAX_ITEMS:
            sanitized_items.append('[truncated-items]')
        return sanitized_items
    if isinstance(value, str):
        return value[:_MAX_STRING_LENGTH]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING_LENGTH]


def sanitize_whatsapp_payload(payload: Any) -> dict[str, Any]:
    if payload in (None, '', {}):
        return {}
    if isinstance(payload, Mapping):
        sanitized = _sanitize_value(payload, depth=0)
        return sanitized if isinstance(sanitized, dict) else {'value': sanitized}
    return {'value': _sanitize_value(payload, depth=0)}
