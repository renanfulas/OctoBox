from django.contrib import admin

from knowledge.models import WodMovementLearnedAlias


@admin.register(WodMovementLearnedAlias)
class WodMovementLearnedAliasAdmin(admin.ModelAdmin):
    list_display = ('raw_text_sample', 'movement_slug', 'hit_count', 'last_seen_at')
    search_fields = ('raw_text_sample', 'raw_text_normalized', 'movement_slug')
    ordering = ('-hit_count',)
