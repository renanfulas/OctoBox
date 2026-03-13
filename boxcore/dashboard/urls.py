"""
ARQUIVO: rotas compativeis do dashboard.

POR QUE ELE EXISTE:
- mantem imports historicos funcionando enquanto as rotas canonicas vivem em dashboard.urls.

O QUE ESTE ARQUIVO FAZ:
1. reexporta as rotas reais do dashboard.

PONTOS CRITICOS:
- este arquivo nao deve voltar a ser a fonte principal das rotas.
"""

from dashboard.urls import urlpatterns

__all__ = ['urlpatterns']