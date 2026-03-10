"""
ARQUIVO: configuração do Django admin para financeiro.

POR QUE ELE EXISTE:
- Agrupa planos, matrículas e pagamentos em um bloco administrativo.
- Mantém o backoffice financeiro já conectado à trilha de auditoria.

O QUE ESTE ARQUIVO FAZ:
1. Define visualização de planos.
2. Define visualização de matrículas.
3. Define visualização de pagamentos.
4. Reaproveita o mixin que audita alterações administrativas sensíveis.

PONTOS CRITICOS:
- Erros aqui atrapalham a operação administrativa e podem enfraquecer a rastreabilidade financeira.
"""

from django.contrib import admin

from .mixins import AuditedAdminMixin
from boxcore.models import Enrollment, MembershipPlan, Payment


@admin.register(MembershipPlan)
class MembershipPlanAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'sessions_per_week', 'active')
    list_filter = ('billing_cycle', 'active')
    search_fields = ('name',)


@admin.register(Enrollment)
class EnrollmentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'plan', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'plan')
    search_fields = ('student__full_name', 'student__phone', 'plan__name')
    autocomplete_fields = ('student', 'plan')


@admin.register(Payment)
class PaymentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'amount', 'due_date', 'status', 'method', 'paid_at')
    list_filter = ('status', 'method', 'due_date')
    search_fields = ('student__full_name', 'student__phone', 'reference')
    autocomplete_fields = ('student', 'enrollment')
    # Esses campos sao tecnicos para agrupamento e nao precisam poluir a edicao manual no admin.
    exclude = ('billing_group', 'installment_number', 'installment_total')