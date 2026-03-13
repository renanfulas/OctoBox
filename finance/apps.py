"""
ARQUIVO: configuracao do app finance.

POR QUE ELE EXISTE:
- transforma finance em app Django leve para consolidar contratos, adapters e superficies de dominio.

O QUE ESTE ARQUIVO FAZ:
1. registra o app finance no projeto.

PONTOS CRITICOS:
- nesta fase o app nao assume app_label nem migrations dos modelos historicos.
"""

from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Finance'
