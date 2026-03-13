"""
ARQUIVO: queries compativeis do snapshot principal do dashboard.

POR QUE ELE EXISTE:
- mantem imports historicos e superficies de patch funcionando enquanto a implementacao canonica vive em dashboard.dashboard_snapshot_queries.

O QUE ESTE ARQUIVO FAZ:
1. reexporta o construtor atual do snapshot.
2. preserva a superficie historica de timezone para testes legados.

PONTOS CRITICOS:
- este arquivo nao deve voltar a concentrar comportamento novo.
"""

from django.utils import timezone

from dashboard.dashboard_snapshot_queries import build_dashboard_snapshot

__all__ = ['build_dashboard_snapshot', 'timezone']