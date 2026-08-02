"""
ARQUIVO: configuracao do app intelligence.

POR QUE ELE EXISTE:
- registra a camada de inteligencia operacional como app Django proprio,
  com app_label e migrations independentes de boxcore.

PONTOS CRITICOS:
- este app nasce com estado proprio e nao deve herdar app_label historico
  de boxcore — nada aqui e verdade primaria transacional.
"""

from django.apps import AppConfig


class IntelligenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intelligence'
    verbose_name = 'Intelligence'
