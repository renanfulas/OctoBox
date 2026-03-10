"""
ARQUIVO: configuração do Django admin para trilha de auditoria.

POR QUE ELE EXISTE:
- Dá visibilidade administrativa aos eventos sensíveis registrados pelo sistema.

O QUE ESTE ARQUIVO FAZ:
1. Publica a trilha de auditoria no admin.
2. Permite filtrar por ator, ação e modelo alvo.
3. Facilita investigação operacional e técnica.

PONTOS CRITICOS:
- Essa tela deve priorizar leitura e investigação, não edição manual.
"""

from django.contrib import admin

from boxcore.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'actor_role', 'action', 'target_model', 'target_label')
    list_filter = ('actor_role', 'action', 'target_model', 'created_at')
    search_fields = ('actor__username', 'target_label', 'description', 'target_id')
    autocomplete_fields = ('actor',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False