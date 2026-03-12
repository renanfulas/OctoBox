"""
ARQUIVO: fachada compatível dos formularios do catalogo.

POR QUE ELE EXISTE:
- Mantem o ponto unico de import enquanto os formularios reais ficam separados por dominio.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta formularios de alunos.
2. Reexporta formularios de financeiro.
3. Reexporta formularios da grade de aulas.

PONTOS CRITICOS:
- Qualquer renomeacao aqui pode quebrar imports espalhados pelo catalogo.
"""

from .form_definitions import (
    ClassGridFilterForm,
    ClassScheduleRecurringForm,
    ClassSessionQuickEditForm,
    EnrollmentManagementForm,
    FinanceFilterForm,
    MembershipPlanQuickForm,
    PaymentManagementForm,
    StudentDirectoryFilterForm,
    StudentQuickForm,
)

__all__ = [
    'ClassGridFilterForm',
    'ClassScheduleRecurringForm',
    'ClassSessionQuickEditForm',
    'EnrollmentManagementForm',
    'FinanceFilterForm',
    'MembershipPlanQuickForm',
    'PaymentManagementForm',
    'StudentDirectoryFilterForm',
    'StudentQuickForm',
]
