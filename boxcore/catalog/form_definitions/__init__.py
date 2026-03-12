"""
ARQUIVO: indice dos formularios do catalogo por dominio.

POR QUE ELE EXISTE:
- Reune os formularios extraidos por assunto sem quebrar imports existentes.

O QUE ESTE ARQUIVO FAZ:
1. Exporta formularios de alunos.
2. Exporta formularios de financeiro.
3. Exporta formularios da grade de aulas.

PONTOS CRITICOS:
- Os nomes exportados aqui sustentam a compatibilidade com o resto do catalogo.
"""

from .class_grid_forms import ClassGridFilterForm, ClassScheduleRecurringForm, ClassSessionQuickEditForm
from .finance_forms import FinanceFilterForm, MembershipPlanQuickForm
from .student_forms import (
    EnrollmentManagementForm,
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