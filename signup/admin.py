"""
ARQUIVO: admin de Early Adopters.

POR QUE ELE EXISTE:
- Da ao operador (Renan) uma interface rapida para ver quem manifestou interesse,
  quem pagou, quem ainda nao ativou e quem cancelou.
- Suporta o follow-up manual via WhatsApp em ate 12h.

O QUE ESTE ARQUIVO FAZ:
1. Lista PendingSignup por status, plano e data.
2. Permite filtros e busca por email/nome do box.
3. Expoe o magic_token (mascarado) para suporte.
"""
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import PendingSignup, PendingSignupStatus


@admin.register(PendingSignup)
class PendingSignupAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'status_badge',
        'full_name',
        'email',
        'box_name',
        'plan',
        'phone',
        'activated_at',
    )
    list_filter = ('status', 'plan', 'created_at')
    search_fields = ('email', 'full_name', 'box_name', 'phone', 'stripe_session_id')
    readonly_fields = (
        'created_at',
        'updated_at',
        'stripe_session_id',
        'stripe_customer_id',
        'stripe_subscription_id',
        'magic_token',
        'magic_token_expires_at',
        'activated_at',
        'activated_user',
        'landing_referer',
    )
    fieldsets = (
        ('Identificacao', {
            'fields': ('full_name', 'email', 'phone', 'box_name'),
        }),
        ('Plano e status', {
            'fields': ('plan', 'status', 'notes'),
        }),
        ('Stripe', {
            'fields': ('stripe_session_id', 'stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',),
        }),
        ('Onboarding', {
            'fields': ('magic_token', 'magic_token_expires_at', 'activated_at', 'activated_user'),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('landing_referer', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        palette = {
            PendingSignupStatus.PENDING: '#9ca3af',
            PendingSignupStatus.PAID: '#10b981',
            PendingSignupStatus.ACTIVATED: '#2563eb',
            PendingSignupStatus.CANCELED: '#6b7280',
            PendingSignupStatus.FAILED: '#ef4444',
        }
        color = palette.get(obj.status, '#9ca3af')
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'background:{};color:#fff;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )
