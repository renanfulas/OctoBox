"""
ARQUIVO: fachada legada do admin financeiro dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a configuracao real vive em finance.admin.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as classes reais do admin financeiro.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar registros novos do admin.
"""

from finance.admin import EnrollmentAdmin, MembershipPlanAdmin, PaymentAdmin


__all__ = ['EnrollmentAdmin', 'MembershipPlanAdmin', 'PaymentAdmin']