"""
ARQUIVO: modelos da central de entrada de alunos.

POR QUE ELE EXISTE:
- Resolve a entrada inicial sem obrigar cadastro manual imediato aluno por aluno.
- Cria uma fila de pré-cadastro que também serve de base para futuras integrações.

O QUE ESTE ARQUIVO FAZ:
1. Registra candidatos, contatos ou entradas vindas de CSV, WhatsApp ou inserção manual.
2. Permite vincular posteriormente esse registro a um aluno definitivo.
3. Organiza o processo de revisão, aprovação e rejeição.

PONTOS CRITICOS:
- O telefone continua sendo uma referência operacional importante.
- Essa camada deve servir de staging antes do cadastro definitivo, não substituir Student.
"""

from django.conf import settings
from django.db import models

from .base import TimeStampedModel
from .students import Student


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
        Student,
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
    raw_payload = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['status', '-created_at']

    def __str__(self):
        return f'{self.full_name} - {self.phone}'