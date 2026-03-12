"""
ARQUIVO: configuracao do app real de jobs.

POR QUE ELE EXISTE:
- Permite instalar a fronteira de jobs como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. Define nome tecnico do app.
2. Mantem jobs como unidade instalavel independente.

PONTOS CRITICOS:
- O nome do app precisa permanecer estavel para evitar churn desnecessario.
"""

from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'
