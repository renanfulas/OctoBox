"""
ARQUIVO: configuracao do app de guia.

POR QUE ELE EXISTE:
- registra o guia interno como app real do runtime.
"""

from django.apps import AppConfig


class GuideConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'guide'
    verbose_name = 'Guide'