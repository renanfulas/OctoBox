"""
ARQUIVO: modelos ligados a alunos.

POR QUE ELE EXISTE:
- Isola a parte cadastral do aluno como um domínio próprio.

O QUE ESTE ARQUIVO FAZ:
1. Define status possíveis do aluno.
2. Define o cadastro principal do aluno.
3. Mantém um telefone principal legado para a operação atual.
4. Guarda dados rápidos de perfil que ajudam o cadastro e a operação.

PONTOS CRITICOS:
- O campo phone ainda sustenta importação e compatibilidade, mas a identidade de canal deve migrar gradualmente para contatos dedicados.
- Mudanças no modelo Student podem afetar financeiro, presença e ocorrências.
"""

from django.db import models

from .base import TimeStampedModel


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
        ordering = ['full_name']

    def __str__(self):
        return self.full_name