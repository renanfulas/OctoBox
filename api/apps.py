"""
ARQUIVO: configuracao do app real de API.

POR QUE ELE EXISTE:
- Permite instalar a fronteira de API como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. Define nome tecnico do app.
2. Mantem a API como unidade instalavel independente.

PONTOS CRITICOS:
- O nome do app precisa permanecer estavel para evitar churn desnecessario no projeto.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
