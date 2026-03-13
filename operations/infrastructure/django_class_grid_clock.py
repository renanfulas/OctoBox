"""
ARQUIVO: adapter Django de tempo da grade de aulas.

POR QUE ELE EXISTE:
- Isola dependencia concreta de timezone para que o adapter principal da grade nao carregue detalhes de framework.

O QUE ESTE ARQUIVO FAZ:
1. Expoe fuso atual.
2. Converte datetimes naive para aware.

PONTOS CRITICOS:
- Dependencias de tempo e timezone devem ficar aqui, nao dentro do fluxo principal da grade.
"""

from django.utils import timezone


class DjangoClassGridClockPort:
    def get_current_timezone(self):
        return timezone.get_current_timezone()

    def make_aware(self, value, current_timezone):
        return timezone.make_aware(value, current_timezone)


__all__ = ['DjangoClassGridClockPort']