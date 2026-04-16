"""
ARQUIVO: contratos base para jobs assincronos.

POR QUE ELE EXISTE:
- define uma interface minima para tarefas que nao devem depender do fluxo HTTP.
- prepara `jobs` para carregar a lingua minima compartilhada da Signal Mesh.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from integrations.mesh import SignalEnvelope, build_signal_envelope


@dataclass(slots=True)
class JobResult:
    success: bool
    message: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)
    envelope: SignalEnvelope | None = None

    def with_envelope(self, envelope: SignalEnvelope | None) -> 'JobResult':
        if envelope is None:
            return self
        self.envelope = envelope
        self.metadata.setdefault('signal_envelope', envelope.to_metadata())
        return self


def build_job_result(
    *,
    success: bool,
    message: str = '',
    metadata: dict[str, Any] | None = None,
    envelope: SignalEnvelope | None = None,
) -> JobResult:
    result = JobResult(success=success, message=message, metadata=metadata or {})
    return result.with_envelope(envelope)


class BaseJob(ABC):
    job_name = 'base-job'

    @staticmethod
    def build_signal_envelope(
        *,
        correlation_id: str = '',
        idempotency_key: str = '',
        source_channel: str = '',
        raw_reference: str = '',
    ) -> SignalEnvelope:
        return build_signal_envelope(
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            source_channel=source_channel,
            raw_reference=raw_reference,
        )

    @abstractmethod
    def run(self, **kwargs) -> JobResult:
        raise NotImplementedError


__all__ = ['BaseJob', 'JobResult', 'build_job_result']
