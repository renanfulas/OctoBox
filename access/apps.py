"""
ARQUIVO: configuracao do app real de acesso.

POR QUE ELE EXISTE:
- Permite instalar a fronteira de acesso como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. Define o nome tecnico do app.
2. Mantem acesso como unidade instalavel independente.

PONTOS CRITICOS:
- O nome do app precisa permanecer estavel para evitar churn desnecessario.
"""

from django.apps import AppConfig


class AccessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'access'
