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
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True, verbose_name='WhatsApp')
    email = models.EmailField(blank=True)
    gender = models.CharField(max_length=16, choices=StudentGender.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    health_issue_status = models.CharField(max_length=8, choices=HealthIssueStatus.choices, blank=True)
    cpf = models.CharField(max_length=14, blank=True)
    status = models.CharField(
        max_length=16,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


__all__ = [
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HealthIssueStatus',
    'Student',
    'StudentGender',
    'StudentStatus',
]