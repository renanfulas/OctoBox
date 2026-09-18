from django.contrib import admin
from django.utils.html import format_html

from .models import (
    PublicWorkoutAssessment,
    PublicWorkoutMovement,
    PublicWorkoutMovementStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
)


@admin.register(PublicWorkoutAssessment)
class PublicWorkoutAssessmentAdmin(admin.ModelAdmin):
    list_display = ('plan_slug', 'measured_at', 'weight_kg', 'body_fat_percent', 'created_at')
    list_filter = ('plan_slug',)
    ordering = ('-measured_at',)
    search_fields = ('plan_slug', 'notes')


@admin.register(PublicWorkoutMovement)
class PublicWorkoutMovementAdmin(admin.ModelAdmin):
    """Revisão do catálogo de movimentos (Onda A0 do CORDA).

    `movement_pattern` extraído automaticamente (`extract_movements_from_html`)
    ganha uma SUGESTÃO de padrão (`classify_public_workout_movements`), mas
    fica `status=pending` até confirmação manual — ver docstring de
    PublicWorkoutMovement/model. Esta tela existe pra essa revisão não
    depender de shell/SQL direto: edita `movement_pattern`/`status` na
    própria listagem, e a ação em lote promove os que já foram conferidos.
    """

    list_display = ('slug', 'label_pt', 'modality', 'movement_pattern', 'status', 'reference_link', 'updated_at')
    list_display_links = ('slug',)
    list_editable = ('label_pt', 'movement_pattern', 'status')
    list_filter = ('status', 'modality')
    search_fields = ('slug', 'label_pt', 'label_en')
    ordering = ('-status', 'slug')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['promote_to_active']

    @admin.display(description='MuscleWiki')
    def reference_link(self, obj):
        if not obj.reference_url:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">abrir</a>', obj.reference_url)

    @admin.action(description='Promover selecionados para "active" (confirma a classificação)')
    def promote_to_active(self, request, queryset):
        updated = queryset.update(status=PublicWorkoutMovementStatus.ACTIVE)
        self.message_user(request, f'{updated} movimento(s) promovido(s) para active.')


class AwaitingActivationFilter(admin.SimpleListFilter):
    """Fila de ativação (Entrega 5, Fase 2, D.2/RT2): quem pagou de verdade
    (status=ACTIVE) mas ainda não tem plan_slug — Renan/esposa ainda não
    criaram o PublicWorkoutProgram/atribuíram o slug. É uma query, não uma
    tabela própria — RT2 exige que isso apareça em algum lugar que se olhe
    todo dia, não que só exista no banco."""

    title = 'aguardando ativação'
    parameter_name = 'aguardando_ativacao'

    def lookups(self, request, model_admin):
        return (('sim', 'Sim — pagou, sem plan_slug'),)

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug__isnull=True)
        return queryset


@admin.register(PublicWorkoutSubscription)
class PublicWorkoutSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('account', 'tier', 'status', 'plan_slug', 'created_at')
    list_filter = (AwaitingActivationFilter, 'tier', 'status')
    search_fields = ('account__email', 'plan_slug')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
