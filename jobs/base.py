"""
ARQUIVO: contratos base para jobs assincronos.

POR QUE ELE EXISTE:
- Define uma interface minima para tarefas que nao devem depender do fluxo HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Define o resultado padrao de execucao de job.
2. Define a interface minima de um job executavel.

PONTOS CRITICOS:
- Jobs devem ser idempotentes e reexecutaveis sempre que possivel.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JobResult:
    success: bool
    message: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseJob(ABC):
    job_name = 'base-job'

    @abstractmethod
    def run(self, **kwargs) -> JobResult:
        raise NotImplementedError
