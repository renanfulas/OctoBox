"""
ARQUIVO: casos de uso dos workflows leves de plano.

POR QUE ELE EXISTE:
- Tira da camada historica do catalogo a orquestracao de criacao e edicao leve de plano.

O QUE ESTE ARQUIVO FAZ:
1. Cria plano com auditoria no mesmo fluxo.
2. Atualiza plano com trilha de campos alterados.

PONTOS CRITICOS:
- A camada de aplicacao nao pode depender de ORM, form ou view.
"""

from .commands import MembershipPlanCommand
from .ports import MembershipPlanAuditPort, MembershipPlanWriterPort, UnitOfWorkPort
from .results import MembershipPlanRecord


def execute_create_membership_plan_use_case(
    command: MembershipPlanCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: MembershipPlanWriterPort,
    audit: MembershipPlanAuditPort,
) -> MembershipPlanRecord:
    def operation():
        result = writer.create(command)
        audit.record_created(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_update_membership_plan_use_case(
    command: MembershipPlanCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: MembershipPlanWriterPort,
    audit: MembershipPlanAuditPort,
) -> MembershipPlanRecord:
    def operation():
        result = writer.update(command)
        audit.record_updated(command=command, result=result)
        return result

    return unit_of_work.run(operation)


__all__ = ['execute_create_membership_plan_use_case', 'execute_update_membership_plan_use_case']