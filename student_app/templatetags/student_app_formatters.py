from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def format_rm_value(value):
    if value in (None, ''):
        return '--'
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if decimal_value == decimal_value.to_integral():
        return f'{int(decimal_value)}kg'
    normalized = format(decimal_value.normalize(), 'f').rstrip('0').rstrip('.')
    return f"{normalized.replace('.', ',')}kg"
