"""
ARQUIVO: admin real do dominio communications.

POR QUE ELE EXISTE:
- Tira a configuracao administrativa de intake e WhatsApp do namespace institucional boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Configura a central de entrada de alunos.
2. Configura contatos e logs de WhatsApp.
3. Reaproveita o mixin de auditoria nas alteracoes do backoffice.

PONTOS CRITICOS:
- Os modelos ainda usam app label historico, por isso as URLs do admin continuam no namespace boxcore.
"""

from django.contrib import admin

from auditing.admin_mixins import AuditedAdminMixin
from shared_support.admin_search import BlindIndexPhoneSearchAdminMixin

from .models import StudentIntake, WhatsAppContact, WhatsAppMessageLog


@admin.register(StudentIntake)
class StudentIntakeAdmin(BlindIndexPhoneSearchAdminMixin, AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'source', 'status', 'linked_student', 'assigned_to')
    list_filter = ('source', 'status')
    search_fields = ('full_name',)
    autocomplete_fields = ('linked_student', 'assigned_to')


@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(BlindIndexPhoneSearchAdminMixin, AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('display_name', 'phone', 'status', 'linked_student', 'last_inbound_at', 'last_outbound_at')
    list_filter = ('status',)
    search_fields = ('display_name', 'linked_student__full_name')
    autocomplete_fields = ('linked_student',)


@admin.register(WhatsAppMessageLog)
class WhatsAppMessageLogAdmin(BlindIndexPhoneSearchAdminMixin, AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('contact', 'direction', 'kind', 'external_message_id', 'created_at')
    list_filter = ('direction', 'kind')
    search_fields = ('contact__display_name', 'external_message_id')
    phone_lookup_path = 'contact__phone_lookup_index'
    autocomplete_fields = ('contact',)


__all__ = ['StudentIntakeAdmin', 'WhatsAppContactAdmin', 'WhatsAppMessageLogAdmin']
