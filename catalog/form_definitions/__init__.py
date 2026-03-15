"""
ARQUIVO: indice dos formularios do catalogo por dominio.

POR QUE ELE EXISTE:
- reune os formularios reais do app catalog por assunto sem depender do namespace legado.

O QUE ESTE ARQUIVO FAZ:
1. exporta formularios de alunos.
2. exporta formularios de financeiro.
3. exporta formularios da grade de aulas.

PONTOS CRITICOS:
- os nomes exportados aqui sustentam a superficie publica de catalog.forms.
"""

from .class_grid_forms import ClassGridFilterForm, ClassScheduleRecurringForm, ClassSessionQuickEditForm
from .finance_forms import FinanceFilterForm, MembershipPlanQuickForm
from .student_forms import (
    EnrollmentManagementForm,
    FinanceCommunicationActionForm,
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