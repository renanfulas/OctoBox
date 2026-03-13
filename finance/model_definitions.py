"""
ARQUIVO: implementacao real dos models de finance.

POR QUE ELE EXISTE:
- Move o ownership de codigo do dominio financeiro para o app real finance sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define enums financeiros e comerciais.
2. Define models concretos de plano, matricula e cobranca.
3. Preserva o app label historico de boxcore e as referencias estruturais necessarias.

PONTOS CRITICOS:
- O ownership de codigo muda aqui, mas o ownership de estado continua em boxcore nesta etapa.
- Campos, validators, ordering e relacionamentos precisam permanecer identicos para evitar migration estrutural.
"""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'
HISTORICAL_BOXCORE_MEMBERSHIP_PLAN_MODEL = 'boxcore.MembershipPlan'
HISTORICAL_BOXCORE_ENROLLMENT_MODEL = 'boxcore.Enrollment'


class EnrollmentStatus(models.TextChoices):
    ACTIVE = 'active', 'Ativa'
    PENDING = 'pending', 'Pendente'
    EXPIRED = 'expired', 'Expirada'
    CANCELED = 'canceled', 'Cancelada'


class BillingCycle(models.TextChoices):
    WEEKLY = 'weekly', 'Semanal'
    MONTHLY = 'monthly', 'Mensal'
    QUARTERLY = 'quarterly', 'Trimestral'
    YEARLY = 'yearly', 'Anual'
    CUSTOM = 'custom', 'Personalizado'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    PAID = 'paid', 'Pago'
    OVERDUE = 'overdue', 'Atrasado'
    CANCELED = 'canceled', 'Cancelado'
    REFUNDED = 'refunded', 'Estornado'


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Dinheiro'
    PIX = 'pix', 'PIX'
    CREDIT_CARD = 'credit_card', 'Cartão de crédito'
    DEBIT_CARD = 'debit_card', 'Cartão de débito'
    BANK_SLIP = 'bank_slip', 'Boleto'
    TRANSFER = 'transfer', 'Transferência'
    OTHER = 'other', 'Outro'


class MembershipPlan(TimeStampedModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(
        max_length=16,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    sessions_per_week = models.PositiveSmallIntegerField(default=3)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['name']

    def __str__(self):
        return self.name


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    plan = models.ForeignKey(
        HISTORICAL_BOXCORE_MEMBERSHIP_PLAN_MODEL,
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.student} - {self.plan}'


class Payment(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    enrollment = models.ForeignKey(
        HISTORICAL_BOXCORE_ENROLLMENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    method = models.CharField(
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PIX,
    )
    billing_group = models.CharField(max_length=36, blank=True)
    installment_number = models.PositiveSmallIntegerField(default=1)
    installment_total = models.PositiveSmallIntegerField(default=1)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['due_date', 'student__full_name']

    def __str__(self):
        return f'{self.student} - {self.amount}'


__all__ = [
    'BillingCycle',
    'Enrollment',
    'EnrollmentStatus',
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_ENROLLMENT_MODEL',
    'HISTORICAL_BOXCORE_MEMBERSHIP_PLAN_MODEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'MembershipPlan',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
]