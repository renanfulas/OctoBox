"""
ARQUIVO: contratos minimos compartilhados da Signal Mesh.

POR QUE ELE EXISTE:
- cria uma lingua comum pequena para webhooks, jobs e sinais assincronos.
- evita que cada corredor invente sua propria etiqueta de rastreabilidade.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SignalEnvelope:
    correlation_id: str = ''
    idempotency_key: str = ''
    source_channel: str = ''
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_reference: str = ''

    def to_metadata(self) -> dict[str, str]:
        return {
            'correlation_id': self.correlation_id,
            'idempotency_key': self.idempotency_key,
            'source_channel': self.source_channel,
            'occurred_at': self.occurred_at.isoformat(),
            'raw_reference': self.raw_reference,
        }


def build_signal_envelope(
    *,
    correlation_id: str = '',
    idempotency_key: str = '',
    source_channel: str = '',
    occurred_at: datetime | None = None,
    raw_reference: str = '',
) -> SignalEnvelope:
    return SignalEnvelope(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        source_channel=source_channel,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        raw_reference=raw_reference,
    )


def build_correlation_id(value: str = '') -> str:
    normalized = (value or '').strip()
    return normalized or uuid4().hex


def calculate_signal_fingerprint(payload: dict) -> str:
    if not payload:
        return ''
    dumped = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(dumped.encode('utf-8')).hexdigest()


def resolve_idempotency_key(
    *,
    explicit_key: str = '',
    event_id: str = '',
    external_id: str = '',
    message_id: str = '',
    provider_reference: str = '',
    fingerprint: str = '',
) -> str:
    for candidate in (
        explicit_key,
        event_id,
        external_id,
        message_id,
        provider_reference,
        fingerprint,
    ):
        normalized = (candidate or '').strip()
        if normalized:
            return normalized
    return ''


def build_idempotency_key(
    *,
    namespace: str = 'octobox',
    action: str,
    primary_reference: str,
    version_reference: str = '',
) -> str:
    key = f'{namespace}_{action}_{primary_reference}'
    if version_reference:
        key = f'{key}_v{version_reference}'
    return key


__all__ = [
    'SignalEnvelope',
    'build_correlation_id',
    'build_idempotency_key',
    'build_signal_envelope',
    'calculate_signal_fingerprint',
    'resolve_idempotency_key',
]
