import re

from django import template
from django.utils.safestring import mark_safe

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
    result = _BREAK_PATTERN.sub('.<br>', text, count=1)
    return mark_safe(result)
