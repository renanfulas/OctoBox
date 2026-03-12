"""
ARQUIVO: fachada legada das rotas da API dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto o modulo real vive em api.urls.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as rotas reais da API.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a ser a fonte principal das rotas.
"""

from api.urls import urlpatterns

__all__ = ['urlpatterns']