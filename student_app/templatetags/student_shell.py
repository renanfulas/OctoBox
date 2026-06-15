"""Tags do shell do app do aluno (saudação do header e copy tempo-relativa).

Mantido separado de student_app_formatters para não misturar formatação de
dados (RM, cargas) com copy do shell. Tudo aqui é tempo-relativo ou de
apresentação — nunca deve ir para snapshots cacheados.
"""
from __future__ import annotations

from django import template
from django.utils import timezone


register = template.Library()

# Acima disso o countdown vira ruído ("em 11h 40min") — a data/hora já informa.
_STARTS_IN_MAX_MINUTES = 12 * 60


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


@register.filter
def starts_in(scheduled_at):
    """Countdown humanizado até a aula ("em 1h 20min"); vazio fora da janela."""
    if not scheduled_at:
        return ''
    total_minutes = int((scheduled_at - timezone.now()).total_seconds() // 60)
    if total_minutes < 0 or total_minutes > _STARTS_IN_MAX_MINUTES:
        return ''
    if total_minutes == 0:
        return 'começando agora'
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f'em {hours}h {minutes}min'
    if hours:
        return f'em {hours}h'
    return f'em {minutes}min'


@register.filter
def complete_count(progress_days):
    """Quantos dias da janela têm ação registrada (streak da semana)."""
    return sum(1 for day in progress_days or () if getattr(day, 'is_complete', False))
