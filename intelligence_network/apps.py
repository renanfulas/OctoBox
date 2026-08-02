"""
ARQUIVO: configuracao do app intelligence_network.

POR QUE ELE EXISTE:
- registra o hub de rede como app SHARED proprio (schema public), com
  app_label e migrations independentes.
"""

from django.apps import AppConfig


class IntelligenceNetworkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intelligence_network'
    verbose_name = 'Intelligence Network'
