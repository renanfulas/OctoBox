"""
ARQUIVO: matching e memoria operacional do dominio quick_sales.

POR QUE ELE EXISTE:
- concentra a normalizacao de descricao, a busca de matches e a promocao de recorrencia para item reutilizavel.

O QUE ESTE ARQUIVO FAZ:
1. normaliza nomes de produto rapido com tolerancia a acento, caixa e ruido leve.
2. resolve match exato por template ou alias.
3. calcula candidatos fuzzy para sugestao.
4. promove recorrencia forte para template reutilizavel.

PONTOS CRITICOS:
- o matching automatico de criacao deve permanecer conservador.
- fuzzy serve como sugestao, nao como verdade operacional silenciosa.
- a promocao nao pode apagar o historico real de vendas anteriores.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from decimal import Decimal
import unicodedata

from django.db.models import Count, Max

from quick_sales.models import QuickProductAlias, QuickProductTemplate, QuickSale, QuickSaleResolutionMode, QuickSaleStatus


PROMOTION_MIN_OCCURRENCES = 3
FUZZY_SUGGESTION_MIN_CONFIDENCE = Decimal('0.780')


def normalize_quick_product_name(raw_value):
    text = str(raw_value or '').strip()
    if not text:
        return ''

    normalized = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(character for character in normalized if not unicodedata.combining(character))
    cleaned = ''.join(character if character.isalnum() else ' ' for character in without_accents.casefold())
    return ' '.join(cleaned.split())


def find_exact_template(normalized_name):
    if not normalized_name:
        return None
    return QuickProductTemplate.objects.filter(
        normalized_name=normalized_name,
        is_active=True,
    ).first()


def find_exact_alias(normalized_name):
    if not normalized_name:
        return None
    return QuickProductAlias.objects.select_related('template').filter(
        normalized_alias_name=normalized_name,
        template__is_active=True,
    ).first()


def find_fuzzy_candidates(normalized_name, *, limit=5):
    if not normalized_name:
        return []

    candidates = []
    seen_template_ids = set()

    for template in QuickProductTemplate.objects.filter(is_active=True).order_by('-usage_count', 'name')[:50]:
        confidence = Decimal(str(round(SequenceMatcher(None, normalized_name, template.normalized_name).ratio(), 3)))
        if confidence < FUZZY_SUGGESTION_MIN_CONFIDENCE:
            continue
        candidates.append(
            {
                'template': template,
                'match_type': QuickSaleResolutionMode.FUZZY_MATCH,
                'confidence': confidence,
                'matched_text': template.normalized_name,
            }
        )
        seen_template_ids.add(template.id)

    for alias in QuickProductAlias.objects.select_related('template').filter(template__is_active=True).order_by('-template__usage_count', 'alias_name')[:50]:
        if alias.template_id in seen_template_ids:
            continue
        confidence = Decimal(str(round(SequenceMatcher(None, normalized_name, alias.normalized_alias_name).ratio(), 3)))
        if confidence < FUZZY_SUGGESTION_MIN_CONFIDENCE:
            continue
        candidates.append(
            {
                'template': alias.template,
                'match_type': QuickSaleResolutionMode.FUZZY_MATCH,
                'confidence': confidence,
                'matched_text': alias.normalized_alias_name,
            }
        )
        seen_template_ids.add(alias.template_id)

    candidates.sort(key=lambda item: (item['confidence'], item['template'].usage_count, item['template'].last_used_at or item['template'].created_at), reverse=True)
    return candidates[:limit]


def resolve_quick_sale_match(raw_value, *, limit=5):
    normalized_name = normalize_quick_product_name(raw_value)
    if not normalized_name:
        return {
            'normalized_name': '',
            'template': None,
            'resolution_mode': QuickSaleResolutionMode.MANUAL,
            'confidence': None,
            'fuzzy_candidates': [],
        }

    template = find_exact_template(normalized_name)
    if template is not None:
        return {
            'normalized_name': normalized_name,
            'template': template,
            'resolution_mode': QuickSaleResolutionMode.EXACT_TEMPLATE,
            'confidence': Decimal('1.000'),
            'fuzzy_candidates': [],
        }

    alias = find_exact_alias(normalized_name)
    if alias is not None:
        return {
            'normalized_name': normalized_name,
            'template': alias.template,
            'resolution_mode': QuickSaleResolutionMode.EXACT_ALIAS,
            'confidence': alias.confidence,
            'fuzzy_candidates': [],
        }

    return {
        'normalized_name': normalized_name,
        'template': None,
        'resolution_mode': QuickSaleResolutionMode.MANUAL,
        'confidence': None,
        'fuzzy_candidates': find_fuzzy_candidates(normalized_name, limit=limit),
    }


def promote_sale_pattern_to_template(*, normalized_description, resolved_description, unit_price):
    if not normalized_description:
        return None

    existing_template = find_exact_template(normalized_description)
    if existing_template is not None:
        return existing_template

    recurring_sales = QuickSale.objects.filter(
        normalized_description=normalized_description,
        unit_price=unit_price,
        status=QuickSaleStatus.PAID,
    )
    recurring_count = recurring_sales.count()
    if recurring_count < PROMOTION_MIN_OCCURRENCES:
        return None

    aggregate = recurring_sales.aggregate(last_used_at=Max('sold_at'))
    template = QuickProductTemplate.objects.create(
        name=resolved_description,
        normalized_name=normalized_description,
        default_unit_price=unit_price,
        usage_count=recurring_count,
        last_used_at=aggregate['last_used_at'],
    )

    QuickProductAlias.objects.get_or_create(
        normalized_alias_name=normalized_description,
        defaults={
            'template': template,
            'alias_name': resolved_description,
            'confidence': Decimal('1.000'),
            'is_auto_generated': True,
        },
    )
    return template


def build_match_snapshot(raw_value, *, limit=5):
    match = resolve_quick_sale_match(raw_value, limit=limit)
    resolved_template = match['template']
    suggestions = []
    for item in match['fuzzy_candidates']:
        template = item['template']
        suggestions.append(
            {
                'template_id': template.id,
                'label': template.name,
                'normalized_name': template.normalized_name,
                'unit_price': f'{template.default_unit_price:.2f}',
                'usage_count': template.usage_count,
                'match_type': item['match_type'],
                'confidence': float(item['confidence']),
            }
        )

    return {
        'normalized_name': match['normalized_name'],
        'resolved_template_id': getattr(match['template'], 'id', None),
        'resolved_template_label': getattr(resolved_template, 'name', ''),
        'resolved_template_unit_price': f'{resolved_template.default_unit_price:.2f}' if resolved_template is not None else '',
        'resolution_mode': match['resolution_mode'],
        'confidence': float(match['confidence']) if match['confidence'] is not None else None,
        'suggestions': suggestions,
    }


__all__ = [
    'FUZZY_SUGGESTION_MIN_CONFIDENCE',
    'PROMOTION_MIN_OCCURRENCES',
    'build_match_snapshot',
    'find_exact_alias',
    'find_exact_template',
    'find_fuzzy_candidates',
    'normalize_quick_product_name',
    'promote_sale_pattern_to_template',
    'resolve_quick_sale_match',
]
