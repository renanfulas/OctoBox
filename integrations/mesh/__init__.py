"""
ARQUIVO: namespace minimo da Signal Mesh.

POR QUE ELE EXISTE:
- reserva um corredor neutro para contratos tecnicos compartilhados da malha.
"""

from .contracts import (
    SignalEnvelope,
    build_correlation_id,
    build_idempotency_key,
    build_signal_envelope,
    calculate_signal_fingerprint,
    resolve_idempotency_key,
)
from .failure_policy import (
    FAILURE_KIND_DUPLICATE,
    FAILURE_KIND_INVALID_PAYLOAD,
    FAILURE_KIND_NON_RETRYABLE,
    FAILURE_KIND_RETRYABLE,
    FAILURE_KIND_UNAUTHORIZED,
    FailureDecision,
    build_failure_decision,
    classify_duplicate,
    classify_invalid_payload,
    classify_non_retryable,
    classify_retryable,
    classify_unauthorized,
)
from .retry_policy import (
    RETRY_ACTION_CONTAIN,
    RETRY_ACTION_GIVE_UP,
    RETRY_ACTION_RETRY,
    RetryDecision,
    build_backoff_delay_seconds,
    decide_retry,
)

__all__ = [
    'SignalEnvelope',
    'FailureDecision',
    'RetryDecision',
    'FAILURE_KIND_DUPLICATE',
    'FAILURE_KIND_INVALID_PAYLOAD',
    'FAILURE_KIND_NON_RETRYABLE',
    'FAILURE_KIND_RETRYABLE',
    'FAILURE_KIND_UNAUTHORIZED',
    'RETRY_ACTION_CONTAIN',
    'RETRY_ACTION_GIVE_UP',
    'RETRY_ACTION_RETRY',
    'build_correlation_id',
    'build_backoff_delay_seconds',
    'build_failure_decision',
    'build_idempotency_key',
    'build_signal_envelope',
    'calculate_signal_fingerprint',
    'classify_duplicate',
    'classify_invalid_payload',
    'classify_non_retryable',
    'classify_retryable',
    'classify_unauthorized',
    'decide_retry',
    'resolve_idempotency_key',
]
