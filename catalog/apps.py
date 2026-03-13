"""
ARQUIVO: configuracao do app catalog.

POR QUE ELE EXISTE:
- registra o app catalog como casca web real das telas de alunos, financeiro e grade.
"""

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'
    verbose_name = 'Catalog'
