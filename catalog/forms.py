"""
ARQUIVO: fachada publica dos formularios do catalogo.

POR QUE ELE EXISTE:
- Permite que o app catalog consuma seus formularios sem depender diretamente do namespace historico boxcore.catalog.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os formularios usados pela casca HTTP do catalogo.

PONTOS CRITICOS:
- A implementacao real continua historica nesta fase; este arquivo so estabiliza a fronteira de importacao.
"""

from boxcore.catalog.forms import (
    ClassScheduleRecurringForm,
    ClassSessionQuickEditForm,
    EnrollmentManagementForm,
    MembershipPlanQuickForm,
    PaymentManagementForm,
    StudentQuickForm,
)

__all__ = [
    'ClassScheduleRecurringForm',
    'ClassSessionQuickEditForm',
    'EnrollmentManagementForm',
    'MembershipPlanQuickForm',
    'PaymentManagementForm',
    'StudentQuickForm',
]