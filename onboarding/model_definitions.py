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


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'


class IntakeSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    CSV = 'csv', 'CSV'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    IMPORT = 'import', 'Importação externa'


class IntakeStatus(models.TextChoices):
    NEW = 'new', 'Novo'
    REVIEWING = 'reviewing', 'Em revisão'
    MATCHED = 'matched', 'Vinculado'
    APPROVED = 'approved', 'Aprovado'
    REJECTED = 'rejected', 'Rejeitado'


class StudentIntake(TimeStampedModel):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    source = models.CharField(
        max_length=16,
        choices=IntakeSource.choices,
        default=IntakeSource.MANUAL,
    )
    status = models.CharField(
        max_length=16,
        choices=IntakeStatus.choices,
        default=IntakeStatus.NEW,
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

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['status', '-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.phone}'


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'IntakeSource',
    'IntakeStatus',
    'StudentIntake',
]