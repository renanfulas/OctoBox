import json

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from . import nutrition_schema
from .models import (
    PublicWorkoutAssessment,
    PublicWorkoutMealPlan,
    PublicWorkoutMovement,
    PublicWorkoutMovementStatus,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
)
from .services import publish_meal_plan


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


@admin.register(PublicWorkoutProfessional)
class PublicWorkoutProfessionalAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'registration_council', 'registration_number', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'registration_number')


class PublicWorkoutMealPlanForm(forms.ModelForm):
    """Entrega 6, Fase 4 (D.6): payload continua sendo JSON estruturado —
    o formulario aceita a forma final como texto JSON (nao um campo por
    refeicao/item, que exigiria um formset aninhado sem lib nova — ver
    plano) e valida a mao contra nutrition_schema antes de aceitar salvar.
    Nunca aceita payload malformado, mesmo digitado direto no admin.
    """

    payload = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 24, 'cols': 100}),
        help_text=(
            'JSON estruturado — schema_version, daily_targets (kcal/protein_g/carbs_g/fat_g) '
            'e meals (meal_id/label/items/substitutes/note). Ver public_workouts/nutrition_schema.py.'
        ),
    )

    class Meta:
        model = PublicWorkoutMealPlan
        fields = ['account', 'authored_by', 'payload']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django reconstroi este form so' com `payload` quando renderiza a
        # tela de leitura de uma versao ja publicada (has_change_permission
        # devolve False, ver PublicWorkoutMealPlanAdmin) — 'authored_by'
        # simplesmente nao existe em self.fields nesse caso.
        if 'authored_by' in self.fields:
            self.fields['authored_by'].queryset = PublicWorkoutProfessional.objects.filter(
                role=PublicWorkoutProfessionalRole.NUTRICAO,
            )
        if self.instance.pk and isinstance(self.instance.payload, dict):
            self.initial['payload'] = json.dumps(self.instance.payload, indent=2, ensure_ascii=False)

    def clean_payload(self):
        raw = self.cleaned_data['payload']
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f'JSON invalido: {exc}') from exc

        errors = nutrition_schema.validate_payload(payload)
        if errors:
            raise forms.ValidationError(errors)
        return payload


@admin.register(PublicWorkoutMealPlan)
class PublicWorkoutMealPlanAdmin(admin.ModelAdmin):
    """Cada save cria uma VERSAO NOVA (D.6, mesmo padrao de
    PublicWorkoutProgram) — nunca UPDATE numa linha existente. `version`/
    `is_active` sao computados por publish_meal_plan, nunca digitados."""

    form = PublicWorkoutMealPlanForm
    list_display = ('account', 'version', 'is_active', 'authored_by', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('account__email',)
    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        if change:
            return  # nunca UPDATE (D.6) — so' novo publish cria versao nova.
        publish_meal_plan(
            account_id=obj.account_id,
            payload=form.cleaned_data['payload'],
            authored_by=obj.authored_by,
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
