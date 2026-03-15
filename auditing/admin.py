"""
ARQUIVO: admin real do dominio de auditoria.

POR QUE ELE EXISTE:
- Centraliza a configuracao administrativa do dominio de auditoria no app real, em vez de concentrar isso no namespace historico boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Publica a trilha de auditoria no admin.
2. Mantem filtros e buscas voltados para investigacao.

PONTOS CRITICOS:
- O modelo ainda usa app label historico, entao a URL final do admin continua no namespace boxcore.
"""

from django.contrib import admin

from access.admin import user_can_access_admin
from auditing.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'actor_role', 'action', 'target_model', 'target_label')
    list_filter = ('actor_role', 'action', 'target_model', 'created_at')
    search_fields = ('actor__username', 'target_label', 'description', 'target_id')
    autocomplete_fields = ('actor',)

    def has_module_permission(self, request):
        return user_can_access_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return user_can_access_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


__all__ = ['AuditEventAdmin']