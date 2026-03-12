"""
ARQUIVO: fachada legada das views da API dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as views reais vivem no app api.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as views reais da API.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from api.views import ApiRootView

__all__ = ['ApiRootView']