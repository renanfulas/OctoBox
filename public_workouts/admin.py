from django.contrib import admin

from .models import PublicWorkoutAssessment


@admin.register(PublicWorkoutAssessment)
class PublicWorkoutAssessmentAdmin(admin.ModelAdmin):
    list_display = ('plan_slug', 'measured_at', 'weight_kg', 'body_fat_percent', 'created_at')
    list_filter = ('plan_slug',)
    ordering = ('-measured_at',)
    search_fields = ('plan_slug', 'notes')
