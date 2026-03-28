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

from django.db import models

from model_support.base import TimeStampedModel
from shared_support.crypto_fields import EncryptedCharField


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


class Student(TimeStampedModel):
    full_name = models.CharField(max_length=150, db_index=True)
    phone = EncryptedCharField(max_length=255, unique=True, verbose_name='WhatsApp')
    phone_lookup_index = models.CharField(max_length=128, db_index=True, blank=True, default='')
    email = models.EmailField(blank=True, db_index=True)
    gender = models.CharField(max_length=16, choices=StudentGender.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    health_issue_status = models.CharField(max_length=8, choices=HealthIssueStatus.choices, blank=True)
    cpf = EncryptedCharField(max_length=255, blank=True)
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


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HealthIssueStatus',
    'Student',
    'StudentGender',
    'StudentStatus',
]
