import json

from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError, models
from django.utils.html import format_html, format_html_join

from . import nutrition_schema, schema
from .models import (
    PublicWorkoutAssessment,
    PublicWorkoutMealPlan,
    PublicWorkoutMovement,
    PublicWorkoutMovementStatus,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftSource,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
)
from .program_generation_ai import generate_program_draft_payload
from .services import (
    ProgramDraftReviewError,
    approve_and_publish_draft,
    create_program_draft,
    flag_movements_against_restrictions,
    get_training_profile,
    publish_meal_plan,
    reject_program_draft,
    serialize_training_profile,
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
        return (('sim', 'Sim — pagou, sem programa ativo'),)

    def queryset(self, request, queryset):
        if self.value() != 'sim':
            return queryset
        # Superset do filtro original (nunca estreita): antes so' pegava
        # plan_slug vazio. Com o rascunho de IA, Renan tipicamente ja'
        # preenche plan_slug ANTES de gerar o rascunho (ver
        # generate_ai_draft abaixo) — sem esta ampliacao, a assinatura
        # "sumiria" da fila no momento exato em que ainda precisa de
        # atencao (rascunho pendente de revisao, ou nenhum rascunho gerado
        # ainda), so' porque plan_slug deixou de ser nulo.
        slugs_com_programa_ativo = PublicWorkoutProgram.objects.filter(is_active=True).values('slug')
        return queryset.filter(status=PublicWorkoutSubscriptionStatus.ACTIVE).filter(
            models.Q(plan_slug__isnull=True) | ~models.Q(plan_slug__in=slugs_com_programa_ativo)
        )


@admin.register(PublicWorkoutSubscription)
class PublicWorkoutSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('account', 'tier', 'status', 'plan_slug', 'created_at')
    list_filter = (AwaitingActivationFilter, 'tier', 'status')
    search_fields = ('account__email', 'plan_slug')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['generate_ai_draft']

    @admin.action(description='Gerar rascunho de treino com IA')
    def generate_ai_draft(self, request, queryset):
        for subscription in queryset:
            if not subscription.plan_slug:
                self.message_user(
                    request, f'{subscription}: defina plan_slug antes de gerar.', level=messages.ERROR
                )
                continue

            profile = get_training_profile(account_id=subscription.account_id)
            if profile is None:
                self.message_user(
                    request, f'{subscription}: aluno ainda não respondeu à anamnese.', level=messages.ERROR
                )
                continue

            training_profile_dict = serialize_training_profile(profile)
            known_slugs = list(
                PublicWorkoutMovement.objects.filter(status=PublicWorkoutMovementStatus.ACTIVE).values_list(
                    'slug', flat=True
                )
            )
            payload, model = generate_program_draft_payload(
                training_profile=training_profile_dict,
                tier=subscription.tier,
                plan_slug=subscription.plan_slug,
                known_movement_slugs=known_slugs,
            )
            if payload is None:
                self.message_user(
                    request,
                    f'{subscription}: geração falhou (sem chave configurada, timeout, ou saída inválida — '
                    'ver logs). Monte manualmente como antes.',
                    level=messages.WARNING,
                )
                continue

            try:
                create_program_draft(
                    account_id=subscription.account_id,
                    slug=subscription.plan_slug,
                    payload=payload,
                    source=PublicWorkoutProgramDraftSource.AI_GENERATED,
                    ai_model=model,
                    training_profile_snapshot=training_profile_dict,
                )
            except IntegrityError:
                self.message_user(
                    request,
                    f'{subscription}: já existe rascunho pendente para este slug — revise-o antes de gerar outro.',
                    level=messages.WARNING,
                )
                continue

            self.message_user(
                request,
                f'{subscription}: rascunho gerado — revise em "Rascunhos de programa" antes de publicar.',
                level=messages.SUCCESS,
            )


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


class PublicWorkoutProgramDraftForm(forms.ModelForm):
    """Mesmo padrao de PublicWorkoutMealPlanForm (payload como texto JSON,
    validado a mao contra schema.validate_payload antes de aceitar salvar)
    — mas AQUI o payload continua EDITAVEL enquanto pending_review: um
    rascunho ainda nao e' o snapshot publicado (isso continua sendo
    PublicWorkoutProgram/publish_program, imutavel, nunca tocado por esta
    tela), entao corrigir o JSON antes de aprovar e' o proprio ponto da
    revisao humana — nao uma excecao a regra de imutabilidade."""

    payload = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 30, 'cols': 100}),
        help_text=(
            'JSON estruturado do programa — schema_version, program_id/program_label/started_on/weeks, '
            'days[].blocks[].movements[], periodization opcional. Ver public_workouts/schema.py.'
        ),
    )

    class Meta:
        model = PublicWorkoutProgramDraft
        fields = ['account', 'slug', 'payload', 'source']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and isinstance(self.instance.payload, dict):
            self.initial['payload'] = json.dumps(self.instance.payload, indent=2, ensure_ascii=False)

    def clean_payload(self):
        raw = self.cleaned_data['payload']
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f'JSON invalido: {exc}') from exc

        errors = schema.validate_payload(payload)
        if errors:
            raise forms.ValidationError(errors)
        return payload


@admin.register(PublicWorkoutProgramDraft)
class PublicWorkoutProgramDraftAdmin(admin.ModelAdmin):
    """A fila de revisão humana obrigatória — NENHUM PublicWorkoutProgram
    nasce de IA (ou de digitação manual, mesmo formulário, `source=manual`)
    sem passar por "Aprovar e publicar" aqui. Decisão confirmada do Renan:
    sempre revisar antes, nunca publicar direto — ver
    services.approve_and_publish_draft, que chama o publish_program já
    existente e não modificado."""

    form = PublicWorkoutProgramDraftForm
    list_display = ('account', 'slug', 'status', 'source', 'ai_model', 'created_at', 'reviewed_at')
    list_filter = ('status', 'source')
    search_fields = ('account__email', 'slug')
    ordering = ('-created_at',)
    readonly_fields = (
        'status',
        'ai_model',
        'generation_error',
        'training_profile_snapshot',
        'reviewed_by',
        'reviewed_at',
        'rejection_reason',
        'created_at',
        'updated_at',
        'restriction_flags_display',
    )
    actions = ['approve_and_publish_action', 'reject_action']

    @admin.display(description='⚠ Movimentos a revisar (restrições declaradas na anamnese)')
    def restriction_flags_display(self, obj):
        if not obj or not obj.pk:
            return '—'
        restrictions = (obj.training_profile_snapshot or {}).get('physical_restrictions') or []
        flags = flag_movements_against_restrictions(payload=obj.payload, physical_restrictions=restrictions)
        if not flags:
            return 'Nenhum candidato encontrado pela heurística — não substitui a leitura completa do payload.'
        items = format_html_join(
            '', '<li><code>{}</code> — restrição declarada: {}</li>', ((f['movement_slug'], f['restriction_tag']) for f in flags)
        )
        return format_html('<ul>{}</ul>', items)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.status != PublicWorkoutProgramDraftStatus.PENDING_REVIEW:
            return False
        return super().has_change_permission(request, obj)

    @admin.action(description='Aprovar e publicar')
    def approve_and_publish_action(self, request, queryset):
        for draft in queryset:
            try:
                program = approve_and_publish_draft(draft_id=draft.pk, reviewed_by=request.user)
            except ProgramDraftReviewError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                continue
            self.message_user(request, f'{draft.slug}: publicado como v{program.version}.', level=messages.SUCCESS)

    @admin.action(description='Rejeitar')
    def reject_action(self, request, queryset):
        rejected = 0
        for draft in queryset:
            try:
                reject_program_draft(
                    draft_id=draft.pk, reviewed_by=request.user, reason='Rejeitado em lote pelo admin.'
                )
                rejected += 1
            except ProgramDraftReviewError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if rejected:
            self.message_user(request, f'{rejected} rascunho(s) rejeitado(s).', level=messages.WARNING)
