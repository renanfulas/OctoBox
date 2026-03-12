"""
ARQUIVO: fachada legada das rotas de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as rotas reais vivem em access.urls.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as rotas reais de acesso.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a ser a fonte principal das rotas.
"""

from access.urls import urlpatterns

__all__ = ['urlpatterns']