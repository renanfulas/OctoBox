"""
ARQUIVO: policy minima de retry da Signal Mesh.

POR QUE ELE EXISTE:
- transforma classificacao de falha em decisao operacional legivel.
- evita que webhook e job calculem retry em lugares diferentes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from .failure_policy import (
    FAILURE_KIND_DUPLICATE,
    FAILURE_KIND_INVALID_PAYLOAD,
    FAILURE_KIND_NON_RETRYABLE,
    FAILURE_KIND_RETRYABLE,
    FAILURE_KIND_UNAUTHORIZED,
)


RETRY_ACTION_RETRY = 'retry'
RETRY_ACTION_CONTAIN = 'contain'
RETRY_ACTION_GIVE_UP = 'give_up'


@dataclass(frozen=True, slots=True)
class RetryDecision:
    action: str
    should_retry: bool
    terminal: bool
    attempt_number: int
    max_attempts: int
    delay_seconds: int = 0
    next_retry_at: datetime | None = None
    failure_kind: str = ''
    reason: str = ''

    def to_metadata(self) -> dict[str, object]:
        return {
            'retry_action': self.action,
            'should_retry': self.should_retry,
            'terminal': self.terminal,
            'attempt_number': self.attempt_number,
            'max_attempts': self.max_attempts,
            'delay_seconds': self.delay_seconds,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else '',
            'failure_kind': self.failure_kind,
            'reason': self.reason,
        }


def build_backoff_delay_seconds(*, attempt_number: int, base_delay_seconds: int = 10, cooldown_seconds: int = 0) -> int:
    safe_attempt_number = max(attempt_number, 1)
    exponential_delay = base_delay_seconds * (2 ** (safe_attempt_number - 1))
    return max(exponential_delay, cooldown_seconds)


def decide_retry(
    *,
    failure_kind: str,
    attempts: int,
    max_attempts: int,
    reason: str = '',
    now: datetime | None = None,
    base_delay_seconds: int = 10,
    cooldown_seconds: int = 0,
) -> RetryDecision:
    current_time = now or timezone.now()
    attempt_number = max(attempts, 0) + 1
    safe_max_attempts = max(max_attempts, 1)

    if failure_kind == FAILURE_KIND_RETRYABLE:
        exhausted = attempt_number >= safe_max_attempts
        if exhausted:
            return RetryDecision(
                action=RETRY_ACTION_GIVE_UP,
                should_retry=False,
                terminal=True,
                attempt_number=attempt_number,
                max_attempts=safe_max_attempts,
                failure_kind=failure_kind,
                reason=reason or 'max-retries-exhausted',
            )

        delay_seconds = build_backoff_delay_seconds(
            attempt_number=attempt_number,
            base_delay_seconds=base_delay_seconds,
            cooldown_seconds=cooldown_seconds,
        )
        return RetryDecision(
            action=RETRY_ACTION_RETRY,
            should_retry=True,
            terminal=False,
            attempt_number=attempt_number,
            max_attempts=safe_max_attempts,
            delay_seconds=delay_seconds,
            next_retry_at=current_time + timedelta(seconds=delay_seconds),
            failure_kind=failure_kind,
            reason=reason or 'retry-scheduled',
        )

    if failure_kind in {FAILURE_KIND_DUPLICATE, FAILURE_KIND_UNAUTHORIZED}:
        return RetryDecision(
            action=RETRY_ACTION_CONTAIN,
            should_retry=False,
            terminal=True,
            attempt_number=attempt_number,
            max_attempts=safe_max_attempts,
            failure_kind=failure_kind,
            reason=reason or 'contained',
        )

    if failure_kind in {FAILURE_KIND_INVALID_PAYLOAD, FAILURE_KIND_NON_RETRYABLE}:
        return RetryDecision(
            action=RETRY_ACTION_GIVE_UP,
            should_retry=False,
            terminal=True,
            attempt_number=attempt_number,
            max_attempts=safe_max_attempts,
            failure_kind=failure_kind,
            reason=reason or 'non-retryable',
        )

    return RetryDecision(
        action=RETRY_ACTION_GIVE_UP,
        should_retry=False,
        terminal=True,
        attempt_number=attempt_number,
        max_attempts=safe_max_attempts,
        failure_kind=failure_kind,
        reason=reason or 'unknown-failure-kind',
    )


__all__ = [
    'RETRY_ACTION_CONTAIN',
    'RETRY_ACTION_GIVE_UP',
    'RETRY_ACTION_RETRY',
    'RetryDecision',
    'build_backoff_delay_seconds',
    'decide_retry',
]
