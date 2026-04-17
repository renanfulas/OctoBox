"""
ARQUIVO: configuracao do app quick_sales.

POR QUE ELE EXISTE:
- registra o dominio de vendas rapidas como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. publica o AppConfig do dominio quick_sales.

PONTOS CRITICOS:
- este app nasce com estado proprio e nao deve herdar app_label historico de boxcore.
"""

from django.apps import AppConfig


class QuickSalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quick_sales'
    verbose_name = 'Quick Sales'
