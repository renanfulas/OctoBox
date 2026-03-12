"""
ARQUIVO: configuracao do app real de communications.

POR QUE ELE EXISTE:
- Permite instalar a fronteira de communications como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. Define o nome tecnico do app.
2. Marca communications como unidade instalavel independente.

PONTOS CRITICOS:
- O nome do app precisa permanecer estavel para reduzir churn na migracao.
"""

from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communications'
