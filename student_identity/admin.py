from django.contrib import admin
from datetime import timedelta
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    StudentAppInvitation,
    StudentIdentity,
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentTransfer,
)


@admin.register(StudentIdentity)
class StudentIdentityAdmin(admin.ModelAdmin):
    list_display = ('student', 'box_root_slug', 'provider', 'email', 'status', 'last_authenticated_at')
    list_filter = ('status', 'provider', 'box_root_slug')
    search_fields = ('student__full_name', 'email', 'provider_subject')


@admin.register(StudentAppInvitation)
class StudentAppInvitationAdmin(admin.ModelAdmin):
    list_display = ('student', 'box_root_slug', 'invited_email', 'invitation_status', 'expires_at', 'accepted_at')
    list_filter = ('box_root_slug',)
    search_fields = ('student__full_name', 'invited_email')
    readonly_fields = ('invite_url',)
    actions = ('extend_selected_invites_by_7_days', 'revoke_selected_invites')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')

    @admin.display(description='Status')
    def invitation_status(self, obj):
        if obj.accepted_at:
            return 'Aceito'
        if obj.is_expired:
            return 'Expirado'
        return 'Pendente'

    @admin.display(description='Link do convite')
    def invite_url(self, obj):
        if obj is None or not getattr(obj, 'pk', None):
            return '-'
        url = reverse('student-identity-invite', kwargs={'token': obj.token})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, url)

    @admin.action(description='Estender validade em 7 dias')
    def extend_selected_invites_by_7_days(self, request, queryset):
        updated = queryset.filter(accepted_at__isnull=True).update(expires_at=timezone.now() + timedelta(days=7))
        self.message_user(request, f'{updated} convite(s) tiveram a validade estendida em 7 dias.')

    @admin.action(description='Revogar convites selecionados')
    def revoke_selected_invites(self, request, queryset):
        updated = queryset.filter(accepted_at__isnull=True).update(expires_at=timezone.now())
        self.message_user(request, f'{updated} convite(s) foram revogados.')


@admin.register(StudentTransfer)
class StudentTransferAdmin(admin.ModelAdmin):
    list_display = ('student', 'from_box_root_slug', 'to_box_root_slug', 'status', 'effective_at')
    list_filter = ('status', 'from_box_root_slug', 'to_box_root_slug')
    search_fields = ('student__full_name', 'reason')


@admin.register(StudentInvitationDelivery)
class StudentInvitationDeliveryAdmin(admin.ModelAdmin):
    list_display = ('invitation', 'channel', 'provider', 'status', 'recipient', 'sent_at', 'failed_at')
    list_filter = ('channel', 'provider', 'status')
    search_fields = ('invitation__student__full_name', 'recipient', 'provider_message_id', 'error_message')


@admin.register(StudentInvitationDeliveryEvent)
class StudentInvitationDeliveryEventAdmin(admin.ModelAdmin):
    list_display = ('delivery', 'provider', 'event_type', 'provider_event_id', 'occurred_at')
    list_filter = ('provider', 'event_type')
    search_fields = ('delivery__invitation__student__full_name', 'provider_event_id', 'event_type')
