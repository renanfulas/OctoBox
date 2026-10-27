"""Authenticate Evolution callbacks and sign an already-normalized receiver payload.

This module deliberately does not parse provider-specific poll payloads or expose
an HTTP endpoint. A parser may call these primitives only after a release-specific
fixture proves where the stable vote ID and clear-text option come from.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from typing import Mapping

from .webhook_auth import (
    MAX_POLL_WEBHOOK_BODY_BYTES,
    _json_without_duplicate_keys,
    _route_secrets_are_unique,
    canonical_poll_webhook_message,
)


MAX_EVOLUTION_JWT_BYTES = 8192
MAX_EVOLUTION_JWT_LIFETIME_SECONDS = 600
EVOLUTION_JWT_FUTURE_SKEW_SECONDS = 60
_SCHEMA_RE = re.compile(r'^box_[a-z0-9_-]{1,59}$')
_BASE64URL_RE = re.compile(r'^[A-Za-z0-9_-]+$')


@dataclass(frozen=True, slots=True)
class EvolutionBridgeRoute:
    """Verified per-instance bridge settings; secret fields never appear in repr."""

    instance_id: str
    schema_name: str
    key_id: str
    jwt_secret: str = field(repr=False)
    hmac_secret: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class EvolutionBridgeFailure:
    code: str
    http_status: int


def _json_object_without_duplicate_keys(raw: bytes) -> dict | None:
    try:
        value = _json_without_duplicate_keys(raw)
    except (UnicodeDecodeError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _decode_base64url(segment: str) -> bytes | None:
    if not segment or not _BASE64URL_RE.fullmatch(segment):
        return None
    try:
        return base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4))
    except (ValueError, binascii.Error):
        return None


def _configured_route(instance_id: str, instances_json: str) -> tuple[EvolutionBridgeRoute | None, EvolutionBridgeFailure | None]:
    try:
        instance_map = _json_without_duplicate_keys(instances_json or '{}')
    except (TypeError, ValueError):
        return None, EvolutionBridgeFailure('webhook-route-config-invalid', 503)
    if not isinstance(instance_map, dict):
        return None, EvolutionBridgeFailure('webhook-route-config-invalid', 503)
    instance = instance_map.get(instance_id)
    if not isinstance(instance, dict):
        return None, EvolutionBridgeFailure('webhook-instance-unknown', 401)

    schema_name = instance.get('schema')
    jwt_secret = instance.get('evolution_jwt_secret')
    key_id = instance.get('active_hmac_key_id')
    keys = instance.get('keys')
    if (
        not isinstance(schema_name, str)
        or not _SCHEMA_RE.fullmatch(schema_name)
        or not isinstance(jwt_secret, str)
        or len(jwt_secret.encode('utf-8')) < 32
        or not isinstance(key_id, str)
        or not key_id
        or len(key_id) > 64
        or any(char in key_id for char in '\r\n')
        or not isinstance(keys, dict)
    ):
        return None, EvolutionBridgeFailure('webhook-route-config-invalid', 503)
    hmac_secret = keys.get(key_id)
    if not isinstance(hmac_secret, str) or len(hmac_secret.encode('utf-8')) < 32:
        return None, EvolutionBridgeFailure('webhook-route-config-invalid', 503)
    if any(
        isinstance(candidate, str)
        and hmac.compare_digest(jwt_secret.encode('utf-8'), candidate.encode('utf-8'))
        for candidate in keys.values()
    ):
        return None, EvolutionBridgeFailure('webhook-secrets-must-be-distinct', 503)
    if not _route_secrets_are_unique(instance_map):
        return None, EvolutionBridgeFailure('webhook-route-config-invalid', 503)
    return EvolutionBridgeRoute(
        instance_id=instance_id,
        schema_name=schema_name,
        key_id=key_id,
        jwt_secret=jwt_secret,
        hmac_secret=hmac_secret,
    ), None


def _verify_evolution_jwt(*, authorization: str, secret: str, now_epoch: int) -> EvolutionBridgeFailure | None:
    if not isinstance(authorization, str) or len(authorization.encode('utf-8')) > MAX_EVOLUTION_JWT_BYTES:
        return EvolutionBridgeFailure('invalid-evolution-authorization', 401)
    parts = authorization.split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1]:
        return EvolutionBridgeFailure('missing-evolution-bearer-token', 401)

    token = parts[1]
    segments = token.split('.')
    if len(segments) != 3:
        return EvolutionBridgeFailure('invalid-evolution-jwt', 401)
    header_bytes = _decode_base64url(segments[0])
    payload_bytes = _decode_base64url(segments[1])
    signature = _decode_base64url(segments[2])
    if header_bytes is None or payload_bytes is None or signature is None or len(signature) != hashlib.sha256().digest_size:
        return EvolutionBridgeFailure('invalid-evolution-jwt', 401)

    header = _json_object_without_duplicate_keys(header_bytes)
    claims = _json_object_without_duplicate_keys(payload_bytes)
    if header is None or claims is None or header.get('alg') != 'HS256':
        return EvolutionBridgeFailure('invalid-evolution-jwt', 401)
    if header.get('typ') not in (None, 'JWT') or any(key in header for key in ('crit', 'b64')):
        return EvolutionBridgeFailure('unsupported-evolution-jwt-header', 401)

    signing_input = f'{segments[0]}.{segments[1]}'.encode('ascii')
    expected = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return EvolutionBridgeFailure('evolution-jwt-signature-mismatch', 401)

    issued_at = claims.get('iat')
    expires_at = claims.get('exp')
    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, int)
    ):
        return EvolutionBridgeFailure('invalid-evolution-jwt-time-claims', 401)
    if issued_at > now_epoch + EVOLUTION_JWT_FUTURE_SKEW_SECONDS:
        return EvolutionBridgeFailure('evolution-jwt-issued-in-future', 401)
    if expires_at <= now_epoch or expires_at <= issued_at:
        return EvolutionBridgeFailure('evolution-jwt-expired', 401)
    if expires_at - issued_at > MAX_EVOLUTION_JWT_LIFETIME_SECONDS:
        return EvolutionBridgeFailure('evolution-jwt-lifetime-too-long', 401)
    not_before = claims.get('nbf')
    if not_before is not None and (isinstance(not_before, bool) or not isinstance(not_before, int) or not_before > now_epoch):
        return EvolutionBridgeFailure('evolution-jwt-not-yet-valid', 401)
    if claims.get('app') != 'evolution' or claims.get('action') != 'webhook':
        return EvolutionBridgeFailure('invalid-evolution-jwt-purpose', 401)
    return None


def authenticate_evolution_callback(
    *,
    headers: Mapping[str, str],
    instances_json: str,
    now_epoch: int | None = None,
) -> tuple[EvolutionBridgeRoute | None, EvolutionBridgeFailure | None]:
    """Authenticate an Evolution JWT against one statically configured instance."""

    instance_id = str(headers.get('X-OctoBox-Instance', '')).strip()
    if not instance_id or len(instance_id) > 128 or any(char in instance_id for char in '\r\n'):
        return None, EvolutionBridgeFailure('missing-evolution-instance', 401)
    route, failure = _configured_route(instance_id, instances_json)
    if failure:
        return None, failure
    token_failure = _verify_evolution_jwt(
        authorization=headers.get('Authorization', ''),
        secret=route.jwt_secret,
        now_epoch=int(time.time()) if now_epoch is None else int(now_epoch),
    )
    if token_failure:
        return None, token_failure
    return route, None


def sign_normalized_poll_payload(
    *,
    route: EvolutionBridgeRoute,
    payload: Mapping[str, object],
    now_epoch: int | None = None,
) -> tuple[bytes | None, dict[str, str] | None, EvolutionBridgeFailure | None]:
    """Serialize a version-validated DTO and sign it for the existing receiver."""

    event_id = payload.get('event_id')
    if (
        not isinstance(event_id, str)
        or not event_id.strip()
        or event_id != event_id.strip()
        or len(event_id) > 255
        or any(c in event_id for c in '\r\n')
    ):
        return None, None, EvolutionBridgeFailure('stable-event-id-required', 400)
    try:
        raw_body = json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(',', ':'),
            allow_nan=False,
        ).encode('utf-8')
    except (TypeError, ValueError):
        return None, None, EvolutionBridgeFailure('normalized-payload-invalid', 400)
    if len(raw_body) > MAX_POLL_WEBHOOK_BODY_BYTES:
        return None, None, EvolutionBridgeFailure('payload-too-large', 413)

    timestamp = str(int(time.time()) if now_epoch is None else int(now_epoch))
    message = canonical_poll_webhook_message(
        instance_id=route.instance_id,
        key_id=route.key_id,
        timestamp=timestamp,
        event_id=event_id,
        raw_body=raw_body,
    )
    signature = hmac.new(route.hmac_secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return raw_body, {
        'X-OctoBox-Instance': route.instance_id,
        'X-OctoBox-Timestamp': timestamp,
        'X-OctoBox-Event-Id': event_id,
        'X-OctoBox-Key-Id': route.key_id,
        'X-OctoBox-Signature': f'v1={signature}',
    }, None


__all__ = [
    'EvolutionBridgeFailure',
    'EvolutionBridgeRoute',
    'authenticate_evolution_callback',
    'sign_normalized_poll_payload',
]
