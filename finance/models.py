"""
ARQUIVO: superficie estavel de modelos do dominio financeiro.

POR QUE ELE EXISTE:
- reduz imports diretos de boxcore.models ao expor o contrato de modelos comerciais e financeiros.

O QUE ESTE ARQUIVO FAZ:
1. reexporta plano, matricula e cobranca.
2. reexporta enums financeiros e comerciais usados em forms, queries e adapters.

PONTOS CRITICOS:
- o ownership de codigo do dominio financeiro ja saiu de boxcore, mas o estado historico do app ainda permanece nesta fase.
"""

from finance.model_definitions import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus

__all__ = [
    'Enrollment',
    'EnrollmentStatus',
    'MembershipPlan',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
]