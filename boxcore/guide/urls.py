"""
ARQUIVO: rotas compativeis do guia interno do sistema.

POR QUE ELE EXISTE:
- mantem imports historicos funcionando enquanto as rotas canonicas vivem em guide.urls.

O QUE ESTE ARQUIVO FAZ:
1. reexporta a rota real do Mapa do Sistema.

PONTOS CRITICOS:
- este arquivo nao deve voltar a ser a fonte principal das rotas.
"""

from guide.urls import urlpatterns

__all__ = ['urlpatterns']