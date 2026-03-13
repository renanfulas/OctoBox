"""
ARQUIVO: bases abstratas compartilhadas de models.

POR QUE ELE EXISTE:
- Separa classes base reutilizaveis do estado historico de boxcore sem alterar schema, app_label ou migrations dos models concretos.

O QUE ESTE ARQUIVO FAZ:
1. Define a base abstrata com timestamps comuns.

PONTOS CRITICOS:
- Alteracoes aqui se propagam para varios models ao mesmo tempo.
- Este modulo deve continuar contendo apenas estruturas abstratas e neutras.
"""

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


__all__ = ['TimeStampedModel']