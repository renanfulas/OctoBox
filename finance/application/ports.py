"""
ARQUIVO: portas dos workflows leves de plano.

POR QUE ELE EXISTE:
- Separa o caso de uso das implementacoes concretas de ORM, auditoria e transacao.

O QUE ESTE ARQUIVO FAZ:
1. Define a escrita de plano.
2. Define a auditoria dos movimentos comerciais.
3. Define a unidade de trabalho do fluxo leve.

PONTOS CRITICOS:
- As portas devem continuar pequenas e focadas neste fluxo.
"""

from collections.abc import Callable
from typing import Protocol, TypeVar

from .commands import MembershipPlanCommand
from .results import MembershipPlanRecord

ReturnType = TypeVar('ReturnType')


class MembershipPlanWriterPort(Protocol):
    def create(self, command: MembershipPlanCommand) -> MembershipPlanRecord:
        ...

    def update(self, command: MembershipPlanCommand) -> MembershipPlanRecord:
        ...


class MembershipPlanAuditPort(Protocol):
    def record_created(self, *, command: MembershipPlanCommand, result: MembershipPlanRecord) -> None:
        ...

    def record_updated(self, *, command: MembershipPlanCommand, result: MembershipPlanRecord) -> None:
        ...


class UnitOfWorkPort(Protocol):
    def run(self, operation: Callable[[], ReturnType]) -> ReturnType:
        ...


__all__ = ['MembershipPlanAuditPort', 'MembershipPlanWriterPort', 'UnitOfWorkPort']