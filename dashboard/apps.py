"""
ARQUIVO: configuracao do app de dashboard.

POR QUE ELE EXISTE:
- registra o dashboard como app real do runtime, separado do estado legado.
"""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = 'Dashboard'