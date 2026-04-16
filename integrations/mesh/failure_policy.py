"""
ARQUIVO: classificacao minima de falha da Signal Mesh.

POR QUE ELE EXISTE:
- cria uma lingua canonica para erros tecnicos da malha.
- evita que cada corredor devolva apenas texto livre para decidir retry ou abandono.
"""

from dataclasses import dataclass


FAILURE_KIND_RETRYABLE = 'retryable'
FAILURE_KIND_NON_RETRYABLE = 'non_retryable'
FAILURE_KIND_DUPLICATE = 'duplicate'
FAILURE_KIND_INVALID_PAYLOAD = 'invalid_payload'
FAILURE_KIND_UNAUTHORIZED = 'unauthorized'


@dataclass(frozen=True, slots=True)
class FailureDecision:
    kind: str
    retryable: bool
    reason: str = ''


def build_failure_decision(*, kind: str, reason: str = '') -> FailureDecision:
    return FailureDecision(
        kind=kind,
        retryable=kind == FAILURE_KIND_RETRYABLE,
        reason=reason,
    )


def classify_duplicate(*, reason: str = 'duplicate') -> FailureDecision:
    return build_failure_decision(kind=FAILURE_KIND_DUPLICATE, reason=reason)


def classify_invalid_payload(*, reason: str = 'invalid-payload') -> FailureDecision:
    return build_failure_decision(kind=FAILURE_KIND_INVALID_PAYLOAD, reason=reason)


def classify_unauthorized(*, reason: str = 'unauthorized') -> FailureDecision:
    return build_failure_decision(kind=FAILURE_KIND_UNAUTHORIZED, reason=reason)


def classify_retryable(*, reason: str = 'retryable') -> FailureDecision:
    return build_failure_decision(kind=FAILURE_KIND_RETRYABLE, reason=reason)


def classify_non_retryable(*, reason: str = 'non-retryable') -> FailureDecision:
    return build_failure_decision(kind=FAILURE_KIND_NON_RETRYABLE, reason=reason)


__all__ = [
    'FAILURE_KIND_DUPLICATE',
    'FAILURE_KIND_INVALID_PAYLOAD',
    'FAILURE_KIND_NON_RETRYABLE',
    'FAILURE_KIND_RETRYABLE',
    'FAILURE_KIND_UNAUTHORIZED',
    'FailureDecision',
    'build_failure_decision',
    'classify_duplicate',
    'classify_invalid_payload',
    'classify_non_retryable',
    'classify_retryable',
    'classify_unauthorized',
]
