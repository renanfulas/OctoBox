"""
ARQUIVO: classes base compartilhadas pelos modelos do sistema.

POR QUE ELE EXISTE:
- Evita repetir campos comuns em todos os modelos.

O QUE ESTE ARQUIVO FAZ:
1. Cria uma base com created_at e updated_at.

PONTOS CRITICOS:
- Alterações nessa base se propagam para vários modelos ao mesmo tempo.
"""

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True