"""
ARQUIVO: actions curtas de plano financeiro.

POR QUE ELE EXISTE:
- evita que a view da central financeira acumule regra de permissao e mutacao.
"""

from access.roles import ROLE_MANAGER, ROLE_OWNER
from catalog.services.membership_plan_workflows import run_membership_plan_create_workflow


def create_membership_plan_from_finance_center(*, actor, current_role, form):
    if current_role.slug not in (ROLE_OWNER, ROLE_MANAGER):
        return {
            'ok': False,
            'reason': 'role-not-allowed',
        }

    plan = run_membership_plan_create_workflow(actor=actor, form=form)
    return {
        'ok': True,
        'plan': plan,
    }
