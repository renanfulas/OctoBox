"""
ARQUIVO: implementacao real dos models de quick_sales.

POR QUE ELE EXISTE:
- cria um dominio transacional proprio para vendas rapidas de balcao sem misturar com mensalidades.

O QUE ESTE ARQUIVO FAZ:
1. define templates reutilizaveis de produto rapido.
2. define aliases para matching e memoria operacional.
3. define a venda rapida concreta vinculada ao aluno.

PONTOS CRITICOS:
- este dominio nao deve reutilizar a tabela de Payment.
- o preco historico da venda precisa viver na propria venda, nunca apenas no template.
- aliases ambiguos quebram a previsibilidade do matching e por isso devem permanecer unicos.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from finance.model_definitions import PaymentMethod
from model_support.base import TimeStampedModel


QUICK_SALES_APP_LABEL = 'quick_sales'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'


class QuickSaleStatus(models.TextChoices):
    PAID = 'paid', 'Pago'
    CANCELED = 'canceled', 'Cancelado'
    REFUNDED = 'refunded', 'Estornado'


class QuickSaleResolutionMode(models.TextChoices):
    EXACT_TEMPLATE = 'exact_template', 'Template exato'
    EXACT_ALIAS = 'exact_alias', 'Alias exato'
    FUZZY_MATCH = 'fuzzy_match', 'Sugestao aproximada'
    MANUAL = 'manual', 'Manual'


class QuickProductTemplate(TimeStampedModel):
    name = models.CharField(max_length=120)
    normalized_name = models.CharField(max_length=120, db_index=True)
    default_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True, db_index=True)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        app_label = QUICK_SALES_APP_LABEL
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['normalized_name'],
                name='uq_quick_product_template_normalized_name',
            ),
        ]
        indexes = [
            models.Index(fields=['is_active', 'usage_count'], name='qs_tpl_active_usage_idx'),
        ]

    def __str__(self):
        return self.name


class QuickProductAlias(TimeStampedModel):
    template = models.ForeignKey(
        'quick_sales.QuickProductTemplate',
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    alias_name = models.CharField(max_length=120)
    normalized_alias_name = models.CharField(max_length=120, db_index=True)
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=1,
        validators=[MinValueValidator(0)],
    )
    is_auto_generated = models.BooleanField(default=False)

    class Meta:
        app_label = QUICK_SALES_APP_LABEL
        ordering = ['alias_name']
        constraints = [
            models.UniqueConstraint(
                fields=['normalized_alias_name'],
                name='uq_quick_product_alias_normalized_name',
            ),
        ]

    def __str__(self):
        return self.alias_name


class QuickSale(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='quick_sales',
    )
    template = models.ForeignKey(
        'quick_sales.QuickProductTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
    )
    typed_description = models.CharField(max_length=120)
    normalized_description = models.CharField(max_length=120, db_index=True)
    resolved_description = models.CharField(max_length=120)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    payment_method = models.CharField(
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PIX,
    )
    status = models.CharField(
        max_length=24,
        choices=QuickSaleStatus.choices,
        default=QuickSaleStatus.PAID,
        db_index=True,
    )
    resolution_mode = models.CharField(
        max_length=24,
        choices=QuickSaleResolutionMode.choices,
        default=QuickSaleResolutionMode.MANUAL,
        db_index=True,
    )
    match_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    sold_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quick_sales',
    )

    class Meta:
        app_label = QUICK_SALES_APP_LABEL
        ordering = ['-sold_at', '-created_at']
        indexes = [
            models.Index(fields=['student', '-sold_at'], name='qs_sale_student_sold_idx'),
            models.Index(fields=['student', 'status'], name='qs_sale_student_status_idx'),
        ]

    def __str__(self):
        return f'{self.resolved_description} - {self.total_amount}'


__all__ = [
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'QUICK_SALES_APP_LABEL',
    'QuickProductAlias',
    'QuickProductTemplate',
    'QuickSale',
    'QuickSaleResolutionMode',
    'QuickSaleStatus',
]
