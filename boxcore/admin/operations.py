"""
ARQUIVO: configuração do Django admin para operação do box.

POR QUE ELE EXISTE:
- Agrupa aula, presença e ocorrências em um bloco administrativo próprio.
- Mantém o backoffice operacional integrado à auditoria administrativa.

O QUE ESTE ARQUIVO FAZ:
1. Configura telas de aulas no admin.
2. Configura telas de presença.
3. Configura telas de ocorrências.
4. Reaproveita o mixin que registra alterações feitas no admin.

PONTOS CRITICOS:
- Não altera o banco, mas mexe diretamente na usabilidade e na rastreabilidade do backoffice operacional.
"""

from django.contrib import admin

from .mixins import AuditedAdminMixin
from boxcore.models import Attendance, BehaviorNote, ClassSession


@admin.register(ClassSession)
class ClassSessionAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'scheduled_at', 'coach', 'capacity', 'status')
    list_filter = ('status', 'scheduled_at')
    search_fields = ('title', 'coach__username')
    autocomplete_fields = ('coach',)


@admin.register(Attendance)
class AttendanceAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'check_in_at', 'check_out_at')
    list_filter = ('status', 'session__scheduled_at')
    search_fields = ('student__full_name', 'student__phone', 'session__title')
    autocomplete_fields = ('student', 'session')


@admin.register(BehaviorNote)
class BehaviorNoteAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'category', 'happened_at', 'author')
    list_filter = ('category', 'happened_at')
    search_fields = ('student__full_name', 'description', 'action_taken')
    autocomplete_fields = ('student', 'author')