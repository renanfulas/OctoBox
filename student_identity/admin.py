from django.contrib import admin
from datetime import timedelta
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    StudentAppInvitation,
    StudentBoxInviteLink,
    StudentIdentity,
    StudentInvitationDelivery,
    StudentInvitationDeliveryEvent,
    StudentTransfer,
)


@admin.register(StudentIdentity)
class StudentIdentityAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'box_root_slug', 'provider', 'email', 'status', 'last_authenticated_at')  # Sprint 2
    list_filter = ('status', 'provider', 'box_root_slug')
    # Student is resolved across schemas by a property, so Admin searches the
    # tenant-independent display snapshot stored on StudentIdentity.
    search_fields = ('student_name', 'email', 'provider_subject')


@admin.register(StudentAppInvitation)
class StudentAppInvitationAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'box_root_slug', 'onboarding_journey', 'invited_email', 'invitation_status', 'expires_at', 'accepted_at')  # Sprint 2
    list_filter = ('box_root_slug', 'onboarding_journey')
    # Email search is exact and routed through its HMAC reader. Substring
    # searches cannot remain valid if invited_email is encrypted later.
    search_fields = ('student_name', 'box_root_slug')
    readonly_fields = ('invite_url',)
    actions = ('extend_selected_invites_by_7_days', 'revoke_selected_invites')

    def get_search_results(self, request, queryset, search_term):
        base_queryset = queryset
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term,
        )
        if '@' not in (search_term or ''):
            return queryset, may_have_duplicates
        from .queries.invitation_email_lookup import invitations_for_email

        matches = invitations_for_email(search_term, queryset=base_queryset)
        if matches:
            queryset = queryset | base_queryset.filter(pk__in=[row.pk for row in matches])
        return queryset, may_have_duplicates

    def get_queryset(self, request):
        return super().get_queryset(request)  # Sprint 2: sem select_related student (cross-schema)

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
    list_display = ('student_id', 'from_box_root_slug', 'to_box_root_slug', 'status', 'effective_at')  # Sprint 2
    list_filter = ('status', 'from_box_root_slug', 'to_box_root_slug')
    # Student is a weak cross-schema reference; search its identity snapshot.
    search_fields = ('identity__student_name', 'reason')


@admin.register(StudentBoxInviteLink)
class StudentBoxInviteLinkAdmin(admin.ModelAdmin):
    list_display = ('box_root_slug', 'use_count', 'max_uses', 'expires_at', 'paused_at', 'revoked_at')
    list_filter = ('box_root_slug',)
    search_fields = ('box_root_slug',)


@admin.register(StudentInvitationDelivery)
class StudentInvitationDeliveryAdmin(admin.ModelAdmin):
    list_display = ('invitation', 'channel', 'provider', 'status', 'recipient', 'sent_at', 'failed_at')
    list_filter = ('channel', 'provider', 'status')
    # Recipient is encrypted; substring search would silently query ciphertext.
    search_fields = ('provider_message_id', 'error_message')


@admin.register(StudentInvitationDeliveryEvent)
class StudentInvitationDeliveryEventAdmin(admin.ModelAdmin):
    list_display = ('delivery', 'provider', 'event_type', 'provider_event_id', 'occurred_at')
    list_filter = ('provider', 'event_type')
    # Invitation.student is cross-schema; the invitation stores student_name.
    search_fields = ('delivery__invitation__student_name', 'provider_event_id', 'event_type')
