"""
ARQUIVO: modelos de comunicação e preparação para WhatsApp.

POR QUE ELE EXISTE:
- Prepara o terreno para integrar WhatsApp no futuro sem depender da API agora.
- Permite registrar vínculo de contato, logs e estado da conversa.

O QUE ESTE ARQUIVO FAZ:
1. Guarda contatos de WhatsApp ligados ou não a alunos.
2. Registra logs de mensagens recebidas e enviadas.
3. Cria uma camada segura para webhooks e automações futuras.

PONTOS CRITICOS:
- Não deve ser confundido com o cadastro definitivo do aluno.
- O raw_payload pode conter dados sensíveis e precisa de cuidado em integrações futuras.
"""

from django.db import models

from .base import TimeStampedModel
from .students import Student


class WhatsAppContactStatus(models.TextChoices):
    NEW = 'new', 'Novo'
    LINKED = 'linked', 'Vinculado'
    OPTED_OUT = 'opted_out', 'Sem consentimento'


class MessageDirection(models.TextChoices):
    INBOUND = 'inbound', 'Entrada'
    OUTBOUND = 'outbound', 'Saída'


class MessageKind(models.TextChoices):
    TEXT = 'text', 'Texto'
    TEMPLATE = 'template', 'Template'
    INTERACTIVE = 'interactive', 'Interativa'
    SYSTEM = 'system', 'Sistema'


class WhatsAppContact(TimeStampedModel):
    phone = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    linked_student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_contacts',
    )
    status = models.CharField(
        max_length=16,
        choices=WhatsAppContactStatus.choices,
        default=WhatsAppContactStatus.NEW,
    )
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    last_outbound_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['display_name', 'phone']

    def __str__(self):
        return self.display_name or self.phone


class WhatsAppMessageLog(TimeStampedModel):
    contact = models.ForeignKey(
        WhatsAppContact,
        on_delete=models.CASCADE,
        related_name='message_logs',
    )
    direction = models.CharField(
        max_length=16,
        choices=MessageDirection.choices,
        default=MessageDirection.INBOUND,
    )
    kind = models.CharField(
        max_length=16,
        choices=MessageKind.choices,
        default=MessageKind.TEXT,
    )
    body = models.TextField(blank=True)
    external_message_id = models.CharField(max_length=120, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.contact} - {self.get_direction_display()}'