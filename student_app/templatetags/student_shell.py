"""Tags do shell do app do aluno (saudação do header).

Mantido separado de student_app_formatters para não misturar formatação de
dados (RM, cargas) com copy do shell.
"""
from __future__ import annotations

from django import template
from django.utils import timezone


register = template.Library()


@register.simple_tag
def student_greeting(full_name: str = '') -> str:
    """Saudação por hora local + primeiro nome ("Boa tarde, Renan")."""
    hour = timezone.localtime().hour
    if hour < 12:
        greeting = 'Bom dia'
    elif hour < 18:
        greeting = 'Boa tarde'
    else:
        greeting = 'Boa noite'

    first_name = (full_name or '').strip().split(' ')[0]
    if first_name:
        return f'{greeting}, {first_name}'
    return greeting
