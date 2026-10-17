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
from finance.models import Enrollment, MembershipPlan, Payment, PartnerCheckInCharge


@admin.register(MembershipPlan)
class MembershipPlanAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'sessions_per_week', 'active')
    list_filter = ('billing_cycle', 'active')
    search_fields = ('name',)


@admin.register(Enrollment)
class EnrollmentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'plan', 'payment_source', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'payment_source', 'plan')
    search_fields = ('student__full_name', 'student__phone', 'plan__name')
    autocomplete_fields = ('student', 'plan')


@admin.register(Payment)
class PaymentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'amount', 'due_date', 'status', 'method', 'paid_at')
    list_filter = ('status', 'method', 'due_date')
    search_fields = ('student__full_name', 'student__phone', 'reference')
    autocomplete_fields = ('student', 'enrollment')
    exclude = ('billing_group', 'installment_number', 'installment_total')
    # Linkage Stripe: preenchido pelo webhook, nao editavel a mao. readonly (em vez
    # de exclude) para o suporte conseguir cruzar o charge no painel da Stripe.
    readonly_fields = (
        'stripe_session_id',
        'stripe_payment_intent_id',
        'stripe_charge_id',
        'currency',
    )


@admin.register(PartnerCheckInCharge)
class PartnerCheckInChargeAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = (
        'enrollment', 'partner', 'status', 'reminder_attempts',
        'declared_value', 'confirmed_at', 'reconciled_at',
    )
    list_filter = ('partner', 'status')
    search_fields = (
        'enrollment__student__full_name', 'enrollment__student__phone',
        'statement_reference',
    )
    autocomplete_fields = ('enrollment', 'attendance')
    readonly_fields = ('reminder_attempts', 'last_reminder_at', 'confirmed_at', 'reconciled_at')


__all__ = ['EnrollmentAdmin', 'MembershipPlanAdmin', 'PartnerCheckInChargeAdmin', 'PaymentAdmin']