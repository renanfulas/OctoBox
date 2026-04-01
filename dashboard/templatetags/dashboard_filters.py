import re

from django import template
from django.utils.html import format_html

register = template.Library()

_BREAK_PATTERN = re.compile(
    r'\. (?=[A-Z])',
)


@register.filter(name='smart_break')
def smart_break(value):
    """Insere <br> apos a primeira frase terminada em '. ' seguida de maiuscula."""
    if not value:
        return value
    text = str(value)
    parts = _BREAK_PATTERN.split(text, maxsplit=1)
    if len(parts) == 2:
        return format_html('{}.<br>{}', parts[0], parts[1])
    return text


@register.filter(name='subtract')
def subtract(value, arg):
    """Subtrai valores numericos simples para uso em markup sem inline style."""
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return value
