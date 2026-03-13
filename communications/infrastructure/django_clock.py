"""
ARQUIVO: adapter Django de clock do dominio de communications.

POR QUE ELE EXISTE:
- Isola o acesso ao tempo atual para que adapters do dominio nao dependam diretamente de django.utils.timezone.

O QUE ESTE ARQUIVO FAZ:
1. Exponibiliza datetime atual do timezone ativo.
2. Exponibiliza data local atual do timezone ativo.

PONTOS CRITICOS:
- Esta camada pode usar Django livremente, mas deve permanecer pequena e puramente tecnica.
"""

from django.utils import timezone

from communications.application.ports import ClockPort


class DjangoClockPort(ClockPort):
    def now(self):
        return timezone.now()

    def today(self):
        return timezone.localdate()


__all__ = ['DjangoClockPort']