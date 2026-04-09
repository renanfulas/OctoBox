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

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'
HISTORICAL_BOXCORE_MEMBERSHIP_PLAN_MODEL = 'boxcore.MembershipPlan'
HISTORICAL_BOXCORE_ENROLLMENT_MODEL = 'boxcore.Enrollment'
HISTORICAL_BOXCORE_PAYMENT_MODEL = 'boxcore.Payment'


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


class FinanceFollowUpStatus(models.TextChoices):
    SUGGESTED = 'suggested', 'Sugerido'
    REALIZED = 'realized', 'Realizado'
    SUPERSEDED = 'superseded', 'Substituido'


class FinanceFollowUpOutcomeStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    SUCCEEDED = 'succeeded', 'Bem-sucedido'
    FAILED = 'failed', 'Falhou'
    EXPIRED = 'expired', 'Expirado'


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
        db_index=True,
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
    due_date = models.DateField(db_index=True)
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
        db_index=True,
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
    version = models.PositiveIntegerField(default=0, help_text="Controle de concorrência otimista")

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['due_date', 'student__full_name']

    def __str__(self):
        return f'{self.student} - {self.amount}'


class FinanceFollowUp(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='finance_follow_ups',
    )
    payment = models.ForeignKey(
        HISTORICAL_BOXCORE_PAYMENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_follow_ups',
    )
    enrollment = models.ForeignKey(
        HISTORICAL_BOXCORE_ENROLLMENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_follow_ups',
    )
    suggestion_key = models.CharField(max_length=180, unique=True, db_index=True)
    source_surface = models.CharField(max_length=32, default='finance_queue', db_index=True)
    signal_bucket = models.CharField(max_length=32, blank=True, db_index=True)
    recommended_action = models.CharField(max_length=64, db_index=True)
    priority_rank = models.PositiveSmallIntegerField(default=0)
    confidence = models.CharField(max_length=16, blank=True)
    prediction_window = models.CharField(max_length=32, blank=True)
    rule_version = models.CharField(max_length=32, blank=True)
    suggestion_window_stage = models.CharField(max_length=16, blank=True, db_index=True)
    suggestion_window_label = models.CharField(max_length=48, blank=True)
    suggestion_window_age_days = models.PositiveSmallIntegerField(null=True, blank=True)
    suggestion_queue_assist_score = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    status = models.CharField(
        max_length=16,
        choices=FinanceFollowUpStatus.choices,
        default=FinanceFollowUpStatus.SUGGESTED,
        db_index=True,
    )
    suggested_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_finance_follow_ups',
    )
    realized_action_kind = models.CharField(max_length=32, blank=True)
    outcome_status = models.CharField(
        max_length=16,
        choices=FinanceFollowUpOutcomeStatus.choices,
        default=FinanceFollowUpOutcomeStatus.PENDING,
        db_index=True,
    )
    outcome_checked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    outcome_window = models.CharField(max_length=16, default='7d')
    outcome_reason = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['status', 'priority_rank', '-suggested_at']

    def __str__(self):
        return f'{self.student} - {self.recommended_action}'


__all__ = [
    'BillingCycle',
    'Enrollment',
    'EnrollmentStatus',
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_ENROLLMENT_MODEL',
    'HISTORICAL_BOXCORE_MEMBERSHIP_PLAN_MODEL',
    'HISTORICAL_BOXCORE_PAYMENT_MODEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'MembershipPlan',
    'FinanceFollowUp',
    'FinanceFollowUpOutcomeStatus',
    'FinanceFollowUpStatus',
    'Payment',
    'PaymentMethod',
    'PaymentStatus',
]
