"""
ARQUIVO: workflows de plano financeiro do catalogo.

POR QUE ELE EXISTE:
- Explicita pelo nome do arquivo que esta camada resolve os workflows publicos de MembershipPlan.

O QUE ESTE ARQUIVO FAZ:
1. Cria planos pela central visual de financeiro.
2. Atualiza planos com trilha de campos alterados.
3. Registra auditoria dos movimentos comerciais ligados ao portfolio de planos.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta o motor comercial usado por matriculas e cobrancas.
"""

from boxcore.auditing import log_audit_event


def run_membership_plan_create_workflow(*, actor, form):
    plan = form.save()
    log_audit_event(
        actor=actor,
        action='membership_plan_quick_created',
        target=plan,
        description='Plano criado pela central visual de financeiro.',
        metadata={'price': str(plan.price), 'billing_cycle': plan.billing_cycle},
    )
    return plan


def run_membership_plan_update_workflow(*, actor, form, changed_fields):
    plan = form.save()
    log_audit_event(
        actor=actor,
        action='membership_plan_quick_updated',
        target=plan,
        description='Plano alterado pela central visual de financeiro.',
        metadata={'changed_fields': changed_fields},
    )
    return plan