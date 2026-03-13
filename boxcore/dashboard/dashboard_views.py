"""
ARQUIVO: view compativel do dashboard principal.

POR QUE ELE EXISTE:
- mantem imports historicos funcionando enquanto a view canonica vive em dashboard.dashboard_views.

O QUE ESTE ARQUIVO FAZ:
1. reexporta a view atual do dashboard.

PONTOS CRITICOS:
- este arquivo nao deve voltar a concentrar comportamento novo.
"""

from dashboard.dashboard_views import DASHBOARD_QUICK_ACTIONS, DashboardView

__all__ = ['DASHBOARD_QUICK_ACTIONS', 'DashboardView']