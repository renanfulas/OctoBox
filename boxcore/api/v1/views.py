"""
ARQUIVO: fachada legada das views v1 da API.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as views reais vivem em api.v1.views.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as views reais da v1.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from api.v1.views import ApiV1HealthView, ApiV1ManifestView

__all__ = ['ApiV1HealthView', 'ApiV1ManifestView']