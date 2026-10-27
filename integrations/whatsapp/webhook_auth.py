"""Authenticate and route Evolution poll callbacks before tenant access.

The configured instance ID is opaque to the sender. Its mapping and secrets
come from deployment configuration; request data never chooses a schema.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Mapping


MAX_POLL_WEBHOOK_BODY_BYTES = 64 * 1024
POLL_WEBHOOK_CLOCK_SKEW_SECONDS = 300
_SCHEMA_RE = re.compile(r"^box_[a-z0-9_-]{1,59}$")
_HEX_SIGNATURE_RE = re.compile(r"^v1=([0-9a-f]{64})$")


@dataclass(frozen=True, slots=True)
class AuthenticatedPollRoute:
    instance_id: str
    schema_name: str
    key_id: str
    event_id: str
    payload: dict


@dataclass(frozen=True, slots=True)
class PollWebhookAuthFailure:
    code: str
    http_status: int


class DuplicateJsonKeyError(ValueError):
    """Raised when JSON contains an object member more than once."""


def _json_without_duplicate_keys(raw: str | bytes):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJsonKeyError('duplicate-json-key')
            result[key] = value
        return result

    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    return json.loads(raw, object_pairs_hook=reject_duplicates)


def _route_secrets_are_unique(instance_map: dict) -> bool:
    seen: list[bytes] = []
    for config in instance_map.values():
        if not isinstance(config, dict):
            continue
        secrets = list((config.get('keys') or {}).values()) if isinstance(config.get('keys'), dict) else []
        secrets.append(config.get('evolution_jwt_secret'))
        for secret in secrets:
            if not isinstance(secret, str) or len(secret.encode('utf-8')) < 32:
                continue
            secret_bytes = secret.encode('utf-8')
            if any(hmac.compare_digest(secret_bytes, previous) for previous in seen):
                return False
            seen.append(secret_bytes)
    return True


def canonical_poll_webhook_message(*, instance_id: str, key_id: str, timestamp: str, event_id: str, raw_body: bytes) -> bytes:
    return (
        b"v1\n"
        + instance_id.encode('utf-8') + b"\n"
        + key_id.encode('utf-8') + b"\n"
        + timestamp.encode('ascii') + b"\n"
        + event_id.encode('utf-8') + b"\n"
        + raw_body
    )


def authenticate_poll_webhook(
    *,
    headers: Mapping[str, str],
    raw_body: bytes,
    instances_json: str,
    now_epoch: int | None = None,
) -> tuple[AuthenticatedPollRoute | None, PollWebhookAuthFailure | None]:
    """Verify timestamp, instance key, raw-body signature, and stable event ID."""

    if len(raw_body) > MAX_POLL_WEBHOOK_BODY_BYTES:
        return None, PollWebhookAuthFailure('payload-too-large', 413)

    instance_id = str(headers.get('X-OctoBox-Instance', '')).strip()
    timestamp = str(headers.get('X-OctoBox-Timestamp', '')).strip()
    event_id = str(headers.get('X-OctoBox-Event-Id', '')).strip()
    key_id = str(headers.get('X-OctoBox-Key-Id', '')).strip()
    signature = str(headers.get('X-OctoBox-Signature', '')).strip()
    if not all((instance_id, timestamp, event_id, key_id, signature)):
        return None, PollWebhookAuthFailure('missing-authentication-header', 401)
    if (
        len(instance_id) > 128
        or len(key_id) > 64
        or len(event_id) > 255
        or any(c in value for value in (instance_id, key_id, event_id, timestamp, signature) for c in '\r\n')
    ):
        return None, PollWebhookAuthFailure('invalid-authentication-header', 401)
    try:
        if not timestamp.isascii() or not timestamp.isdigit():
            raise ValueError
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return None, PollWebhookAuthFailure('invalid-timestamp', 401)
    current_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
    if abs(current_epoch - timestamp_value) > POLL_WEBHOOK_CLOCK_SKEW_SECONDS:
        return None, PollWebhookAuthFailure('timestamp-outside-window', 401)

    try:
        instance_map = _json_without_duplicate_keys(instances_json or '{}')
    except (TypeError, ValueError):
        return None, PollWebhookAuthFailure('webhook-route-config-invalid', 503)
    if not isinstance(instance_map, dict):
        return None, PollWebhookAuthFailure('webhook-route-config-invalid', 503)
    if not _route_secrets_are_unique(instance_map):
        return None, PollWebhookAuthFailure('webhook-route-config-invalid', 503)
    instance = instance_map.get(instance_id)
    if not isinstance(instance, dict):
        return None, PollWebhookAuthFailure('webhook-instance-unknown', 401)
    schema_name = instance.get('schema')
    keys = instance.get('keys')
    if not isinstance(schema_name, str) or not _SCHEMA_RE.fullmatch(schema_name) or not isinstance(keys, dict):
        return None, PollWebhookAuthFailure('webhook-route-config-invalid', 503)
    secret = keys.get(key_id)
    if not isinstance(secret, str) or len(secret.encode('utf-8')) < 32:
        code = 'webhook-key-unknown' if secret is None else 'webhook-route-config-invalid'
        status = 401 if secret is None else 503
        return None, PollWebhookAuthFailure(code, status)
    signature_match = _HEX_SIGNATURE_RE.fullmatch(signature)
    if not signature_match:
        return None, PollWebhookAuthFailure('invalid-signature-format', 401)

    expected = hmac.new(
        secret.encode('utf-8'),
        canonical_poll_webhook_message(
            instance_id=instance_id,
            key_id=key_id,
            timestamp=timestamp,
            event_id=event_id,
            raw_body=raw_body,
        ),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature_match.group(1), expected):
        return None, PollWebhookAuthFailure('signature-mismatch', 401)

    try:
        payload = _json_without_duplicate_keys(raw_body)
    except (UnicodeDecodeError, ValueError):
        return None, PollWebhookAuthFailure('invalid-json', 400)
    if not isinstance(payload, dict):
        return None, PollWebhookAuthFailure('invalid-payload-shape', 400)
    if payload.get('event_id') != event_id:
        return None, PollWebhookAuthFailure('event-id-mismatch', 400)

    return AuthenticatedPollRoute(
        instance_id=instance_id,
        schema_name=schema_name,
        key_id=key_id,
        event_id=event_id,
        payload=payload,
    ), None


__all__ = [
    'AuthenticatedPollRoute',
    'MAX_POLL_WEBHOOK_BODY_BYTES',
    'POLL_WEBHOOK_CLOCK_SKEW_SECONDS',
    'PollWebhookAuthFailure',
    'authenticate_poll_webhook',
    'canonical_poll_webhook_message',
]
