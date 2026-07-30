"""
ARQUIVO: implementacao real dos models de onboarding.

POR QUE ELE EXISTE:
- Move o ownership de codigo do intake para o app real onboarding sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define enums e model concreto de intake.
2. Preserva o app label historico de boxcore.
3. Explicita as referencias historicas necessarias para manter schema e migrations estaveis.

PONTOS CRITICOS:
- O ownership de codigo muda aqui, mas o ownership de estado continua em boxcore nesta etapa.
- Campos, ordering e relacionamentos precisam permanecer identicos para evitar migration estrutural.
"""

from django.conf import settings
from django.db import models

from model_support.base import TimeStampedModel
from shared_support.crypto_fields import EncryptedCharField


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'


class IntakeSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    CSV = 'csv', 'Indicação'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    IMPORT = 'import', 'Importação externa'


class IntakeStatus(models.TextChoices):
    NEW = 'new', 'Novo'
    REVIEWING = 'reviewing', 'Em revisão'
    MATCHED = 'matched', 'Vinculado'
    APPROVED = 'approved', 'Aprovado'
    REJECTED = 'rejected', 'Rejeitado'


class StudentIntake(TimeStampedModel):
    full_name = models.CharField(max_length=150, db_index=True)
    phone = EncryptedCharField(max_length=255, db_index=True)
    phone_lookup_index = models.CharField(max_length=128, db_index=True, blank=True, default='')
    email = EncryptedCharField(max_length=255, blank=True, db_index=True)
    source = models.CharField(
        max_length=16,
        choices=IntakeSource.choices,
        default=IntakeSource.MANUAL,
    )
    status = models.CharField(
        max_length=16,
        choices=IntakeStatus.choices,
        default=IntakeStatus.NEW,
        db_index=True,
    )
    linked_student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intake_records',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_intakes',
    )
    raw_payload = models.JSONField(blank=True, default=dict)
    notes = models.TextField(blank=True)

    # Marcadores de desfecho do funil. Sem eles, so o estado ATUAL era
    # conhecido — impossivel montar janela de maturacao ou separar "lead
    # perdido" de "lead recente que ainda nao teve tempo de converter"
    # (censura a direita). Ver auditoria de leads 2026-07-28, achado M18.
    first_contacted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    converted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    rejected_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Distingue COMO a conversao aconteceu (ex: 'enrollment'), para nao
    # confundir com o marcador de vinculo de identidade (linked_student),
    # que o convite tambem preenche sem que isso seja conversao comercial.
    conversion_kind = models.CharField(max_length=24, blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['status', '-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.phone}'

    def save(self, *args, **kwargs):
        from shared_support.crypto_fields import generate_blind_index
        # Dual-Write: Garante que o intake ja nasca ou seja atualizado com o indice de busca.
        if self.phone:
            self.phone_lookup_index = generate_blind_index(self.phone)
        else:
            self.phone_lookup_index = ""
        super().save(*args, **kwargs)


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'IntakeSource',
    'IntakeStatus',
    'StudentIntake',
]
