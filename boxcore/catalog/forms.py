"""
ARQUIVO: fachada compatível dos formularios do catalogo.

POR QUE ELE EXISTE:
- mantem o ponto unico de import historico enquanto a superficie canonica vive em catalog.forms.

O QUE ESTE ARQUIVO FAZ:
1. reexporta os formularios publicos atuais do catalogo.

PONTOS CRITICOS:
- qualquer renomeacao aqui pode quebrar imports historicos espalhados pelo runtime legado.
"""

from catalog.forms import (
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
