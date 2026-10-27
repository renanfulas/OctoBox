"""Admin registrations whose email fields require exact lookup adapters."""

from django.contrib import admin
from django.utils import timezone

from public_workouts.admin_email_search import PublicWorkoutCommerceExactEmailSearchMixin
from public_workouts.email_lookup import checkout_leads_for_email, waitlist_entries_for_email
from public_workouts.models import (
    PublicWorkoutCheckoutLead,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
)


@admin.register(PublicWorkoutCheckoutLead)
class PublicWorkoutCheckoutLeadAdmin(PublicWorkoutCommerceExactEmailSearchMixin, admin.ModelAdmin):
    list_display = ('email', 'tier', 'marketing_consent', 'paid_at', 'created_at')
    list_editable = ('marketing_consent',)
    list_filter = ('tier', 'marketing_consent', 'paid_at', 'created_at')
    search_fields = ('email',)
    email_lookup = staticmethod(checkout_leads_for_email)
    readonly_fields = [
        field.name for field in PublicWorkoutCheckoutLead._meta.fields
        if field.name not in ('marketing_consent', 'marketing_consent_at')
    ]
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if 'marketing_consent' in form.changed_data:
            obj.marketing_consent_at = timezone.now() if obj.marketing_consent else None
        super().save_model(request, obj, form, change)


@admin.register(PublicWorkoutWaitlistEntry)
class PublicWorkoutWaitlistEntryAdmin(PublicWorkoutCommerceExactEmailSearchMixin, admin.ModelAdmin):
    list_display = ('email', 'tier', 'status', 'created_at', 'invited_at', 'expires_at')
    list_filter = ('status', 'tier', 'created_at')
    search_fields = ('email',)
    email_lookup = staticmethod(waitlist_entries_for_email)
    readonly_fields = (
        'email', 'tier', 'acquisition_session', 'consented_at', 'invited_at',
        'expires_at', 'converted_at', 'created_at', 'updated_at',
    )
    actions = ('queue_invitation', 'cancel_selected')

    def has_add_permission(self, request):
        return False

    @admin.action(description='Colocar convite na fila de envio')
    def queue_invitation(self, request, queryset):
        from public_workouts.outbox import TOPIC_WAITLIST_INVITE, enqueue_outbox

        queued = 0
        for entry in queryset.filter(status=PublicWorkoutWaitlistStatus.WAITING):
            enqueue_outbox(
                topic=TOPIC_WAITLIST_INVITE,
                aggregate_type='waitlist', aggregate_id=entry.pk,
                version=max(1, entry.pk),
            )
            queued += 1
        self.message_user(request, f'{queued} convite(s) colocado(s) na outbox.')

    @admin.action(description='Cancelar entradas selecionadas')
    def cancel_selected(self, request, queryset):
        count = queryset.filter(
            status__in=(PublicWorkoutWaitlistStatus.WAITING, PublicWorkoutWaitlistStatus.INVITED),
        ).update(status=PublicWorkoutWaitlistStatus.CANCELED)
        self.message_user(request, f'{count} entrada(s) cancelada(s).')
