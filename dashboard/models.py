from django.conf import settings
from django.db import models


class DashboardLayoutPreference(models.Model):
    # on_delete=DO_NOTHING (não CASCADE): este model é TENANT_APPS (só existe em
    # cada schema box_xxx), mas User é SHARED_APPS (schema public). O collector
    # de delete do Django resolve nome de tabela pelo search_path da conexão
    # ativa — ao deletar um User a partir de public, CASCADE faz o Django tentar
    # consultar dashboard_dashboardlayoutpreference ali, onde ela não existe, e
    # quebra com UndefinedTable pra QUALQUER user vinculado a algum box. Limpeza
    # cross-schema correta fica em control.services.delete_user_safely().
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name='dashboard_layout_preferences')
    role_slug = models.CharField(max_length=32)
    layout = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'role_slug')