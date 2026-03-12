"""
ARQUIVO: fachada legada das views de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as views reais vivem em access.views.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as views reais de acesso.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.views import AccessOverviewView, HomeRedirectView

__all__ = ['AccessOverviewView', 'HomeRedirectView']