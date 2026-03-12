"""
ARQUIVO: fachada legada das rotas v1 da API.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as rotas reais vivem em api.v1.urls.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as rotas reais da v1.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a ser a fonte principal das rotas.
"""

from api.v1.urls import urlpatterns

__all__ = ['urlpatterns']