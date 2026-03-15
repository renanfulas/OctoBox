"""
ARQUIVO: superficie publica dos formularios do catalogo.

POR QUE ELE EXISTE:
- permite que o app catalog consuma seus formularios pelo proprio dominio, com implementacao real fora do namespace legado.

O QUE ESTE ARQUIVO FAZ:
1. reexporta os formularios usados pela casca HTTP do catalogo.

PONTOS CRITICOS:
- os nomes exportados aqui sustentam views, queries e testes do catalogo.
"""

from .form_definitions import (
    ClassGridFilterForm,
    ClassScheduleRecurringForm,
    ClassSessionQuickEditForm,
    EnrollmentManagementForm,
    FinanceCommunicationActionForm,
    FinanceFilterForm,
    MembershipPlanQuickForm,
    PaymentManagementForm,
    ReceptionPaymentManagementForm,
    StudentPaymentActionForm,
    StudentDirectoryFilterForm,
    StudentQuickForm,
)

__all__ = [
    'ClassGridFilterForm',
    'ClassScheduleRecurringForm',
    'ClassSessionQuickEditForm',
    'EnrollmentManagementForm',
    'FinanceCommunicationActionForm',
    'FinanceFilterForm',
    'MembershipPlanQuickForm',
    'PaymentManagementForm',
    'ReceptionPaymentManagementForm',
    'StudentPaymentActionForm',
    'StudentDirectoryFilterForm',
    'StudentQuickForm',
]