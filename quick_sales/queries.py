"""
ARQUIVO: snapshots e consultas leves do dominio quick_sales.

POR QUE ELE EXISTE:
- entrega memoria operacional reutilizavel para a ficha do aluno sem vazar ORM cru.

O QUE ESTE ARQUIVO FAZ:
1. monta recentes clicaveis de vendas rapidas.
2. monta sugestoes de templates reutilizaveis.
3. combina ambos em um snapshot serializavel para o front.

PONTOS CRITICOS:
- o contrato precisa permanecer JSON-first.
- memoria nao deve depender de heuristica opaca para parecer consistente ao operador.
"""

from quick_sales.models import QuickProductTemplate, QuickSale, QuickSaleStatus
from quick_sales.services.matching import build_match_snapshot, normalize_quick_product_name


def build_student_quick_sale_recent_snapshot(student_id, *, limit=6):
    recent_sales = QuickSale.objects.filter(
        student_id=student_id,
        status=QuickSaleStatus.PAID,
    ).order_by('-sold_at', '-created_at')

    seen_keys = set()
    recent_items = []
    for sale in recent_sales:
        memory_key = (sale.normalized_description, str(sale.unit_price))
        if memory_key in seen_keys:
            continue
        seen_keys.add(memory_key)
        recent_items.append(
            {
                'quick_sale_id': sale.id,
                'template_id': sale.template_id,
                'label': sale.resolved_description,
                'normalized_name': sale.normalized_description,
                'unit_price': f'{sale.unit_price:.2f}',
                'payment_method': sale.payment_method,
                'sold_at': sale.sold_at.isoformat(),
            }
        )
        if len(recent_items) >= limit:
            break
    return recent_items


def build_student_quick_sale_history_snapshot(student_id, *, limit=5):
    sales = QuickSale.objects.filter(student_id=student_id).order_by('-sold_at', '-created_at')[:limit]
    history_items = []
    for sale in sales:
        history_items.append(
            {
                'quick_sale_id': sale.id,
                'label': sale.resolved_description,
                'unit_price': f'{sale.unit_price:.2f}',
                'status': sale.status,
                'status_label': sale.get_status_display(),
                'payment_method': sale.payment_method,
                'sold_at_label': sale.sold_at.strftime('%d/%m/%Y %H:%M'),
                'can_cancel': sale.status == QuickSaleStatus.PAID,
                'can_refund': sale.status == QuickSaleStatus.PAID,
            }
        )
    return history_items


def build_quick_sale_template_snapshot(*, limit=6):
    templates = QuickProductTemplate.objects.filter(is_active=True).order_by('-usage_count', '-last_used_at', 'name')[:limit]
    return [
        {
            'template_id': template.id,
            'label': template.name,
            'normalized_name': template.normalized_name,
            'unit_price': f'{template.default_unit_price:.2f}',
            'usage_count': template.usage_count,
            'last_used_at': template.last_used_at.isoformat() if template.last_used_at else None,
        }
        for template in templates
    ]


def build_quick_sale_memory_snapshot(*, student_id, query='', limit=6):
    normalized_query = normalize_quick_product_name(query)
    match_snapshot = build_match_snapshot(query, limit=limit) if normalized_query else {
        'normalized_name': '',
        'resolved_template_id': None,
        'resolution_mode': 'manual',
        'confidence': None,
        'suggestions': [],
    }
    return {
        'query': query,
        'normalized_query': normalized_query,
        'match': match_snapshot,
        'recent': build_student_quick_sale_recent_snapshot(student_id, limit=limit),
        'templates': build_quick_sale_template_snapshot(limit=limit),
    }


__all__ = [
    'build_student_quick_sale_history_snapshot',
    'build_quick_sale_memory_snapshot',
    'build_quick_sale_template_snapshot',
    'build_student_quick_sale_recent_snapshot',
]
