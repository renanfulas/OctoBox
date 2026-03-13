"""
ARQUIVO: admin real do dominio operacional.

POR QUE ELE EXISTE:
- Move o backoffice operacional para o app real de operations, em vez de concentrar essa configuracao no namespace historico.

O QUE ESTE ARQUIVO FAZ:
1. Configura aulas no admin.
2. Configura presencas no admin.
3. Configura ocorrencias no admin.

PONTOS CRITICOS:
- O app label historico ainda e preservado nos modelos, entao a URL final do admin continua apontando para boxcore.
"""

from django.contrib import admin

from auditing.admin_mixins import AuditedAdminMixin
from operations.models import Attendance, BehaviorNote, ClassSession


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


__all__ = ['AttendanceAdmin', 'BehaviorNoteAdmin', 'ClassSessionAdmin']