"""
ARQUIVO: implementacao real dos models de students.

POR QUE ELE EXISTE:
- Move o ownership de codigo do cadastro de alunos para o app real students sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define enums do dominio de alunos.
2. Define o model concreto Student.
3. Preserva o app label historico de boxcore.

PONTOS CRITICOS:
- O ownership de codigo muda aqui, mas o ownership de estado continua em boxcore nesta etapa.
- Campos, ordering e comportamento precisam permanecer identicos para evitar migration estrutural.
"""

from django.conf import settings
from django.db import models

from model_support.base import TimeStampedModel
from shared_support.crypto_fields import EncryptedCharField
from shared_support.acquisition import (
    ACQUISITION_CHANNEL_MODEL_CHOICES,
    SOURCE_CONFIDENCE_CHOICES,
    SOURCE_RESOLUTION_METHOD_CHOICES,
)


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'


class StudentStatus(models.TextChoices):
    LEAD = 'lead', 'Lead'
    ACTIVE = 'active', 'Ativo'
    PAUSED = 'paused', 'Pausado'
    INACTIVE = 'inactive', 'Inativo'


class StudentGender(models.TextChoices):
    MALE = 'male', 'Masculino'
    FEMALE = 'female', 'Feminino'


class HealthIssueStatus(models.TextChoices):
    YES = 'yes', 'Sim'
    NO = 'no', 'Nao'


class SourceConfidence(models.TextChoices):
    UNKNOWN = 'unknown', 'Desconhecida'
    HIGH = 'high', 'Alta'
    MEDIUM = 'medium', 'Media'
    LOW = 'low', 'Baixa'


class SourceResolutionMethod(models.TextChoices):
    INTAKE_AUTO = 'intake_auto', 'Intake automatico'
    MANUAL_FORM = 'manual_form', 'Formulario manual'
    MANUAL_REVIEW = 'manual_review', 'Revisao manual'
    DECLARED_ONLY = 'declared_only', 'Somente declarado'
    LEGACY = 'legacy', 'Legado'


class Student(TimeStampedModel):
    full_name = models.CharField(max_length=150, db_index=True)
    phone = EncryptedCharField(max_length=255, unique=True, verbose_name='WhatsApp')
    phone_lookup_index = models.CharField(max_length=128, db_index=True, blank=True, default='')
    email = models.EmailField(blank=True, db_index=True)
    gender = models.CharField(max_length=16, choices=StudentGender.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    health_issue_status = models.CharField(max_length=8, choices=HealthIssueStatus.choices, blank=True)
    cpf = EncryptedCharField(max_length=255, blank=True)
    acquisition_source = models.CharField(max_length=32, choices=ACQUISITION_CHANNEL_MODEL_CHOICES, blank=True, db_index=True)
    acquisition_source_detail = models.CharField(max_length=120, blank=True)
    resolved_acquisition_source = models.CharField(max_length=32, choices=ACQUISITION_CHANNEL_MODEL_CHOICES, blank=True, db_index=True)
    resolved_source_detail = models.CharField(max_length=120, blank=True)
    source_confidence = models.CharField(max_length=16, choices=SOURCE_CONFIDENCE_CHOICES, default=SourceConfidence.UNKNOWN)
    source_conflict_flag = models.BooleanField(default=False)
    source_resolution_method = models.CharField(max_length=24, choices=SOURCE_RESOLUTION_METHOD_CHOICES, blank=True)
    source_resolution_reason = models.CharField(max_length=64, blank=True)
    source_captured_at = models.DateTimeField(null=True, blank=True)
    source_captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='captured_students',
    )
    status = models.CharField(
        max_length=16,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['phone_lookup_index'],
                condition=~models.Q(phone_lookup_index=''),
                name='unique_non_blank_student_phone_lookup_index',
            )
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        from shared_support.crypto_fields import generate_blind_index
        # Dual-Write: Sincroniza o índice determinístico com o telefone criptografado.
        if self.phone:
            self.phone_lookup_index = generate_blind_index(self.phone)
        else:
            self.phone_lookup_index = ""
        super().save(*args, **kwargs)


class StudentSourceDeclaration(TimeStampedModel):
    student = models.ForeignKey('boxcore.Student', on_delete=models.CASCADE, related_name='source_declarations')
    declared_acquisition_source = models.CharField(max_length=32, choices=ACQUISITION_CHANNEL_MODEL_CHOICES, db_index=True)
    declared_source_detail = models.CharField(max_length=120, blank=True)
    declared_source_channel = models.CharField(max_length=32, blank=True)
    declared_source_response_id = models.CharField(max_length=120, blank=True, db_index=True)
    captured_at = models.DateTimeField(db_index=True)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='captured_student_source_declarations',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-captured_at', '-created_at']

    def __str__(self):
        return f'{self.student_id}:{self.declared_acquisition_source}'


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HealthIssueStatus',
    'SourceConfidence',
    'SourceResolutionMethod',
    'Student',
    'StudentSourceDeclaration',
    'StudentGender',
    'StudentStatus',
]
