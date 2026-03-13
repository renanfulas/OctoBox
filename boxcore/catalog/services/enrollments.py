"""
ARQUIVO: fachada do motor de matrícula do catálogo.

POR QUE ELE EXISTE:
- Mantem o contrato historico de matrícula enquanto a superfície canônica vive em catalog.services.enrollments.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os helpers públicos atuais de matrícula.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar ORM, transação ou geração de cobrança.
"""

from catalog.services.enrollments import (
    cancel_enrollment,
    describe_plan_change,
    reactivate_enrollment,
    sync_student_enrollment,
)


__all__ = [
    'cancel_enrollment',
    'describe_plan_change',
    'reactivate_enrollment',
    'sync_student_enrollment',
]