"""
ARQUIVO: modelos do domínio financeiro e comercial.

POR QUE ELE EXISTE:
- Separa planos, matrículas e pagamentos da operação de aula.

O QUE ESTE ARQUIVO FAZ:
1. Define ciclos de cobrança e status financeiros.
2. Define planos de academia.
3. Liga aluno ao plano por meio de matrícula.
4. Registra pagamentos, vencimentos, formas de pagamento e agrupamentos comerciais.

PONTOS CRITICOS:
- Alterações aqui afetam relatórios, inadimplência e futuras integrações de cobrança.
- Campos de status e valor são sensíveis e não devem mudar sem revisão do impacto.
"""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .base import TimeStampedModel
from .students import Student


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
        ordering = ['name']

    def __str__(self):
        return self.name


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name='enrollments')
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.student} - {self.plan}'


class Payment(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    enrollment = models.ForeignKey(
        Enrollment,
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
    # billing_group e os campos de parcela permitem tratar cobrancas relacionadas como um mesmo pacote comercial.
    billing_group = models.CharField(max_length=36, blank=True)
    installment_number = models.PositiveSmallIntegerField(default=1)
    installment_total = models.PositiveSmallIntegerField(default=1)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['due_date', 'student__full_name']

    def __str__(self):
        return f'{self.student} - {self.amount}'