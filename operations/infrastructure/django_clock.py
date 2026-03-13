"""
ARQUIVO: adapter Django de tempo das mutacoes operacionais.

POR QUE ELE EXISTE:
- Isola dependencia concreta de tempo para que adapters operacionais nao dependam diretamente de timezone.

O QUE ESTE ARQUIVO FAZ:
1. Expoe o instante atual para actions do workspace.

PONTOS CRITICOS:
- Dependencias de tempo devem ficar aqui, nao dentro do fluxo operacional principal.
"""

from django.utils import timezone


class DjangoWorkspaceClockPort:
    def now(self):
        return timezone.now()


__all__ = ['DjangoWorkspaceClockPort']