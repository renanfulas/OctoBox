"""
ARQUIVO: modelo de auditoria de ações sensíveis.

POR QUE ELE EXISTE:
- Cria uma base rastreável para integridade, governança e revisão ética.
- Prepara o projeto para acessos técnicos e futuros acessos de contingência.

O QUE ESTE ARQUIVO FAZ:
1. Registra quem executou uma ação sensível.
2. Guarda papel, ação, alvo e descrição resumida do evento.
3. Armazena metadados úteis para investigação posterior.

PONTOS CRITICOS:
- Auditoria deve ser append-only na prática de negócio, mesmo que o Django gere permissão de delete.
- O conteúdo salvo aqui pode sustentar investigação interna e não deve ser adulterado sem política clara.
"""

from django.conf import settings
from django.db import models

from .base import TimeStampedModel


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
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} - {self.target_model or "sistema"}'