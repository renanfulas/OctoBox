"""
ARQUIVO: actions transacionais do dominio quick_sales.

POR QUE ELE EXISTE:
- concentra mutacoes de venda rapida em um ponto simples, previsivel e reutilizavel.

O QUE ESTE ARQUIVO FAZ:
1. cria uma venda rapida paga.
2. cancela uma venda rapida.
3. estorna uma venda rapida.

PONTOS CRITICOS:
- a venda precisa preservar descricao e preco historicos.
- template e opcional, mas quando presente deve atualizar memoria operacional basica.
- cancelamento e estorno alteram estado, nunca apagam historico.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from quick_sales.models import QuickProductTemplate, QuickSale, QuickSaleResolutionMode, QuickSaleStatus
from quick_sales.services.matching import normalize_quick_product_name, promote_sale_pattern_to_template, resolve_quick_sale_match


def _normalize_description(raw_value):
    return ' '.join(str(raw_value or '').strip().split())


def _resolve_template(template_id):
    if not template_id:
        return None
    return QuickProductTemplate.objects.filter(pk=template_id, is_active=True).first()


@transaction.atomic
def create_quick_sale(*, actor, student, payload):
    template = _resolve_template(payload.get('template_id'))
    description = _normalize_description(payload.get('description') or getattr(template, 'name', ''))
    if not description:
        raise ValueError('Descricao do pagamento rapido ausente.')

    amount = payload.get('amount')
    if amount is None:
        raise ValueError('Valor do pagamento rapido ausente.')
    if amount <= 0:
        raise ValueError('Valor do pagamento rapido deve ser maior que zero.')

    resolution_mode = QuickSaleResolutionMode.MANUAL
    resolved_description = description
    normalized_description = normalize_quick_product_name(description)
    match_confidence = None
    if template is None:
        match = resolve_quick_sale_match(description)
        template = match['template']
        resolution_mode = match['resolution_mode']
        match_confidence = match['confidence']
    if template is not None:
        resolved_description = template.name
        normalized_description = template.normalized_name
        if resolution_mode == QuickSaleResolutionMode.MANUAL:
            resolution_mode = QuickSaleResolutionMode.EXACT_TEMPLATE
        if match_confidence is None:
            match_confidence = 1

    sale = QuickSale.objects.create(
        student=student,
        template=template,
        typed_description=description,
        normalized_description=normalized_description,
        resolved_description=resolved_description,
        quantity=1,
        unit_price=amount,
        total_amount=amount,
        payment_method=payload.get('method') or 'pix',
        status=QuickSaleStatus.PAID,
        resolution_mode=resolution_mode,
        match_confidence=match_confidence,
        reference=payload.get('reference') or '',
        notes=payload.get('notes') or '',
        sold_at=payload.get('sold_at') or timezone.now(),
        created_by=actor,
    )

    if template is not None:
        QuickProductTemplate.objects.filter(pk=template.pk).update(
            usage_count=F('usage_count') + 1,
            last_used_at=sale.sold_at,
        )
        template.refresh_from_db(fields=['usage_count', 'last_used_at'])
        sale.template = template
    else:
        promoted_template = promote_sale_pattern_to_template(
            normalized_description=sale.normalized_description,
            resolved_description=sale.resolved_description,
            unit_price=sale.unit_price,
        )
        if promoted_template is not None:
            sale.template = promoted_template

    return sale


@transaction.atomic
def cancel_quick_sale(*, actor, student, quick_sale, payload=None):
    payload = payload or {}
    sale = QuickSale.objects.select_for_update().get(pk=quick_sale.pk, student=student)
    if sale.status == QuickSaleStatus.CANCELED:
        return sale
    if sale.status != QuickSaleStatus.PAID:
        raise ValueError('Apenas vendas pagas podem ser canceladas.')

    sale.status = QuickSaleStatus.CANCELED
    if payload.get('notes'):
        sale.notes = payload['notes']
    sale.save(update_fields=['status', 'notes', 'updated_at'])
    return sale


@transaction.atomic
def refund_quick_sale(*, actor, student, quick_sale, payload=None):
    payload = payload or {}
    sale = QuickSale.objects.select_for_update().get(pk=quick_sale.pk, student=student)
    if sale.status == QuickSaleStatus.REFUNDED:
        return sale
    if sale.status != QuickSaleStatus.PAID:
        raise ValueError('Apenas vendas pagas podem ser estornadas.')

    sale.status = QuickSaleStatus.REFUNDED
    if payload.get('notes'):
        sale.notes = payload['notes']
    sale.save(update_fields=['status', 'notes', 'updated_at'])
    return sale


__all__ = [
    'cancel_quick_sale',
    'create_quick_sale',
    'refund_quick_sale',
]
