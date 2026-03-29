"""
ARQUIVO: implementacao real dos models de WhatsApp do dominio communications.

POR QUE ELE EXISTE:
- Tira a implementacao real dos models de WhatsApp de dentro de boxcore sem trocar ainda o app label historico.

O QUE ESTE ARQUIVO FAZ:
1. Define enums do dominio de comunicacao via WhatsApp.
2. Define contato de WhatsApp e log de mensagens.
3. Mantem `app_label = 'boxcore'` para preservar estado do Django e schema atual.

PONTOS CRITICOS:
- O ownership do codigo muda aqui, mas o estado do Django continua pertencendo a boxcore nesta etapa.
- Campos, constraints, ordering e relacionamento precisam permanecer identicos para evitar migration estrutural.
"""

from django.db import models

from model_support.base import TimeStampedModel
from shared_support.crypto_fields import EncryptedCharField, EncryptedTextField


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'
HISTORICAL_BOXCORE_WHATSAPP_CONTACT_MODEL = 'boxcore.WhatsAppContact'


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
    phone = EncryptedCharField(max_length=255, unique=True)
    phone_lookup_index = models.CharField(max_length=128, db_index=True, blank=True, default='')
    external_contact_id = models.CharField(max_length=120, blank=True)
    display_name = models.CharField(max_length=150, blank=True)
    linked_student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
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
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['display_name', 'phone']
        constraints = [
            models.UniqueConstraint(
                fields=['external_contact_id'],
                condition=~models.Q(external_contact_id=''),
                name='unique_non_blank_whatsapp_external_contact_id',
            ),
            models.UniqueConstraint(
                fields=['phone_lookup_index'],
                condition=~models.Q(phone_lookup_index=''),
                name='unique_non_blank_whatsapp_phone_lookup_index',
            )
        ]

    def __str__(self):
        return self.display_name or self.phone

    def save(self, *args, **kwargs):
        from shared_support.crypto_fields import generate_blind_index
        # Dual-Write: Mantem o indice pesquisavel em sincronia com o PII criptografado.
        if self.phone:
            self.phone_lookup_index = generate_blind_index(self.phone)
        else:
            self.phone_lookup_index = ""
        super().save(*args, **kwargs)


class WhatsAppMessageLog(TimeStampedModel):
    contact = models.ForeignKey(
        HISTORICAL_BOXCORE_WHATSAPP_CONTACT_MODEL,
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
    body = EncryptedTextField(blank=True)
    external_message_id = models.CharField(max_length=120, blank=True, db_index=True)
    webhook_fingerprint = models.CharField(max_length=128, blank=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(blank=True, default=dict)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['external_message_id'],
                condition=~models.Q(external_message_id=''),
                name='unique_non_blank_whatsapp_external_message_id',
            ),
            models.UniqueConstraint(
                fields=['webhook_fingerprint'],
                condition=~models.Q(webhook_fingerprint=''),
                name='unique_non_blank_whatsapp_webhook_fingerprint',
            )
        ]

    def __str__(self):
        return f'{self.contact} - {self.get_direction_display()}'


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'HISTORICAL_BOXCORE_WHATSAPP_CONTACT_MODEL',
    'MessageDirection',
    'MessageKind',
    'WhatsAppContact',
    'WhatsAppContactStatus',
    'WhatsAppMessageLog',
]
