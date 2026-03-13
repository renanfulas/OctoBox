"""
ARQUIVO: admin real do dominio de alunos.

POR QUE ELE EXISTE:
- Move a configuracao administrativa de Student para o app real de students.

O QUE ESTE ARQUIVO FAZ:
1. Define colunas, filtros e busca do cadastro de alunos.
2. Reaproveita o mixin de auditoria nas alteracoes do backoffice.

PONTOS CRITICOS:
- O modelo ainda depende do estado historico, entao a URL do admin continua no namespace boxcore nesta fase.
"""

from django.contrib import admin

from auditing.admin_mixins import AuditedAdminMixin
from students.models import Student


@admin.register(Student)
class StudentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'status', 'updated_at')
    list_filter = ('status', 'gender', 'health_issue_status')
    search_fields = ('full_name', 'phone', 'email')
    ordering = ('full_name',)


__all__ = ['StudentAdmin']