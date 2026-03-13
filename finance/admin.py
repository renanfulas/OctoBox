"""
ARQUIVO: admin real do dominio financeiro.

POR QUE ELE EXISTE:
- Move a configuracao administrativa de planos, matriculas e pagamentos para o app real de finance.

O QUE ESTE ARQUIVO FAZ:
1. Configura a visualizacao de planos.
2. Configura a visualizacao de matriculas.
3. Configura a visualizacao de pagamentos.

PONTOS CRITICOS:
- Os modelos continuam ancorados no estado historico, entao o namespace final do admin ainda nao muda nesta fase.
"""

from django.contrib import admin

from auditing.admin_mixins import AuditedAdminMixin
from finance.models import Enrollment, MembershipPlan, Payment


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
    exclude = ('billing_group', 'installment_number', 'installment_total')


__all__ = ['EnrollmentAdmin', 'MembershipPlanAdmin', 'PaymentAdmin']