"""
ARQUIVO: fachada das leituras de alunos do catalogo.

POR QUE ELE EXISTE:
- mantem um ponto unico de import para snapshots do catalogo enquanto os corredores internos ficam separados por capacidade.
"""

from catalog.student_directory_queries import (
    _enrich_student_directory_display_students,
    build_student_directory_listing_snapshot,
    build_student_directory_snapshot,
    build_student_directory_support_snapshot,
)
from catalog.student_financial_queries import (
    build_student_financial_snapshot,
    compute_fidalgometro_score,
    get_operational_enrollment,
    get_operational_payment_status,
    get_operational_payment_status_label,
)


__all__ = [
    'build_student_directory_listing_snapshot',
    'build_student_directory_support_snapshot',
    'build_student_directory_snapshot',
    'build_student_financial_snapshot',
    'compute_fidalgometro_score',
    'get_operational_enrollment',
    'get_operational_payment_status',
    'get_operational_payment_status_label',
]
