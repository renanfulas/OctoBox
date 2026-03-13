"""
ARQUIVO: fachada dos workflows leves de plano.

POR QUE ELE EXISTE:
- Mantem a interface publica atual do catalogo enquanto a orquestracao real sai da camada historica e entra em use cases com adapters dedicados.

O QUE ESTE ARQUIVO FAZ:
1. Traduz form.cleaned_data para um command explicito.
2. Chama o fluxo concreto do dominio financeiro leve.
3. Devolve o model historico esperado pelas views e testes atuais.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar ORM, auditoria ou transacao.
"""

from finance.application.commands import build_membership_plan_command
from finance.infrastructure import (
    execute_create_membership_plan_command,
    execute_update_membership_plan_command,
)
from finance.models import MembershipPlan


def run_membership_plan_create_workflow(*, actor, form):
    command = build_membership_plan_command(
        actor_id=getattr(actor, 'id', None),
        cleaned_data=form.cleaned_data,
    )
    result = execute_create_membership_plan_command(command)
    return MembershipPlan.objects.get(pk=result.id)


def run_membership_plan_update_workflow(*, actor, form, changed_fields):
    command = build_membership_plan_command(
        actor_id=getattr(actor, 'id', None),
        cleaned_data=form.cleaned_data,
        plan_id=getattr(getattr(form, 'instance', None), 'id', None),
        changed_fields=tuple(changed_fields),
    )
    result = execute_update_membership_plan_command(command)
    return MembershipPlan.objects.get(pk=result.id)