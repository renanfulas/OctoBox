"""
ARQUIVO: configuração do Django admin para alunos.

POR QUE ELE EXISTE:
- Separa o backoffice de aluno em um arquivo específico.
- Mantém mudanças cadastrais de aluno já integradas à auditoria administrativa.

O QUE ESTE ARQUIVO FAZ:
1. Define como o cadastro de aluno aparece no admin.
2. Define colunas, filtros e busca do módulo de alunos.
3. Reaproveita o mixin de auditoria nas alterações feitas pelo backoffice.

PONTOS CRITICOS:
- Mudanças aqui afetam a usabilidade do admin de alunos e a qualidade da trilha de rastreio.
"""

from django.contrib import admin

from .mixins import AuditedAdminMixin
from boxcore.models import Student


@admin.register(Student)
class StudentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'status', 'updated_at')
    list_filter = ('status', 'gender', 'health_issue_status')
    search_fields = ('full_name', 'phone', 'email')
    ordering = ('full_name',)