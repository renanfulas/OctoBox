"""
ARQUIVO: fachada publica do dominio quick_sales.

POR QUE ELE EXISTE:
- oferece portas estaveis para registrar, cancelar e estornar vendas rapidas.

O QUE ESTE ARQUIVO FAZ:
1. publica a criacao de venda rapida.
2. publica cancelamento e estorno de venda rapida.

PONTOS CRITICOS:
- a fachada deve permanecer fina para nao virar lugar de regra espalhada.
"""

from quick_sales.services.quick_sale_actions import (
    cancel_quick_sale,
    create_quick_sale,
    refund_quick_sale,
)
from quick_sales.queries import build_quick_sale_memory_snapshot
from quick_sales.services.matching import build_match_snapshot


def run_quick_sale_create(*, actor, student, payload):
    return create_quick_sale(actor=actor, student=student, payload=payload)


def run_quick_sale_cancel(*, actor, student, quick_sale, payload=None):
    return cancel_quick_sale(actor=actor, student=student, quick_sale=quick_sale, payload=payload)


def run_quick_sale_refund(*, actor, student, quick_sale, payload=None):
    return refund_quick_sale(actor=actor, student=student, quick_sale=quick_sale, payload=payload)


def run_quick_sale_match(*, raw_query, limit=5):
    return build_match_snapshot(raw_query, limit=limit)


def run_quick_sale_memory_snapshot(*, student_id, query='', limit=6):
    return build_quick_sale_memory_snapshot(student_id=student_id, query=query, limit=limit)


__all__ = [
    'run_quick_sale_cancel',
    'run_quick_sale_create',
    'run_quick_sale_match',
    'run_quick_sale_memory_snapshot',
    'run_quick_sale_refund',
]
