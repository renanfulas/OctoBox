"""
ARQUIVO: fachada legada dos models de finance dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real do dominio financeiro vive em finance.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta enums e models reais de finance.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real dos models.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from finance.model_definitions import (
    BillingCycle,
    Enrollment,
    EnrollmentStatus,
    MembershipPlan,
    Payment,
    PaymentMethod,
    PaymentStatus,
)


__all__ = [
    'BillingCycle',
    'Enrollment',
    'EnrollmentStatus',
    'MembershipPlan',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
]