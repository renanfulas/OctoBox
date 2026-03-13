"""
ARQUIVO: implementacao real do model de auditoria.

POR QUE ELE EXISTE:
- Move o ownership de codigo de AuditEvent para o app real auditing sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define o model concreto de auditoria.
2. Preserva o app label historico de boxcore.

PONTOS CRITICOS:
- O ownership de codigo muda aqui, mas o ownership de estado continua em boxcore nesta etapa.
- Estrutura e ordering precisam permanecer identicos para evitar migration estrutural.
"""

from django.conf import settings
from django.db import models

from model_support.base import TimeStampedModel


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'


class AuditEvent(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    actor_role = models.CharField(max_length=40, blank=True)
    action = models.CharField(max_length=80)
    target_model = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    target_label = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} - {self.target_model or "sistema"}'


__all__ = ['AuditEvent', 'HISTORICAL_BOXCORE_APP_LABEL']