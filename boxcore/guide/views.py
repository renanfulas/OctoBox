"""
ARQUIVO: view compativel do guia interno do sistema.

POR QUE ELE EXISTE:
- mantem imports historicos funcionando enquanto a view canonica vive em guide.views.

O QUE ESTE ARQUIVO FAZ:
1. reexporta a view atual do Mapa do Sistema.

PONTOS CRITICOS:
- este arquivo nao deve voltar a concentrar comportamento novo.
"""

from guide.views import SystemMapView

__all__ = ['SystemMapView']