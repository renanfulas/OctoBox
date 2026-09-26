import json

from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError, models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from . import nutrition_schema, schema
from .models import (
    PublicWorkoutAccount,
    PublicWorkoutAssessment,
    PublicWorkoutCampaignSpend,
    PublicWorkoutAcquisitionSession,
    PublicWorkoutFunnelEvent,
    PublicWorkoutMealPlan,
    PublicWorkoutMealPlanDelivery,
    PublicWorkoutMetricSnapshot,
    PublicWorkoutMovement,
    PublicWorkoutMovementStatus,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutProgram,
    PublicWorkoutProgramDelivery,
    PublicWorkoutRefundRequest,
    PublicWorkoutRefundRequestStatus,
    PublicWorkoutOutboxMessage,
    PublicWorkoutOutboxStatus,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftSource,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTestimonial,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
)
from .widgets import NutritionPlanEditorWidget
from .notifications import notify_program_ready
from .services import (
    ProgramDraftReviewError,
    approve_and_publish_draft,
    flag_movements_against_restrictions,
    publish_meal_plan,
    reject_program_draft,
)


@admin.register(PublicWorkoutAcquisitionSession)
class PublicWorkoutAcquisitionSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'first_source', 'first_medium', 'last_source', 'last_medium',
        'account', 'subscription', 'first_seen_at', 'last_seen_at',
    )
    list_filter = ('first_medium', 'last_medium', 'offer_version')
    search_fields = ('id', 'first_source', 'last_source', 'first_campaign', 'last_campaign')
    ordering = ('-last_seen_at',)
    readonly_fields = [field.name for field in PublicWorkoutAcquisitionSession._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PublicWorkoutFunnelEvent)
class PublicWorkoutFunnelEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'tier', 'channel', 'source', 'campaign', 'occurred_at')
    list_filter = ('event_type', 'tier', 'channel', 'occurred_at')
    search_fields = ('event_id', 'source', 'campaign', 'correlation_id')
    ordering = ('-occurred_at',)
    readonly_fields = [field.name for field in PublicWorkoutFunnelEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PublicWorkoutWorkItem)
class PublicWorkoutWorkItemAdmin(admin.ModelAdmin):
    list_display = (
        'account', 'item_type', 'status', 'age', 'is_overdue', 'priority', 'assigned_to',
        'due_at', 'estimated_effort_minutes', 'actual_effort_minutes',
    )
    list_filter = ('status', 'item_type', 'priority', 'assigned_to', 'due_at')
    search_fields = ('account__email', 'cycle_key', 'blocked_reason')
    ordering = ('priority', 'due_at', 'created_at')
    readonly_fields = (
        'account', 'subscription', 'item_type', 'cycle_key', 'status', 'priority',
        'estimated_effort_minutes', 'created_at', 'updated_at',
    )
    actions = ('start_selected', 'complete_selected', 'block_selected')

    @admin.display(description='Idade')
    def age(self, obj):
        delta = timezone.now() - obj.created_at
        return f'{delta.days}d {delta.seconds // 3600}h'

    @admin.display(boolean=True, description='Atrasado')
    def is_overdue(self, obj):
        return obj.status not in (
            PublicWorkoutWorkItemStatus.DONE, PublicWorkoutWorkItemStatus.CANCELED,
        ) and obj.due_at < timezone.now()

    @admin.action(description='Iniciar itens selecionados')
    def start_selected(self, request, queryset):
        from .operations import transition_work_item
        for item in queryset:
            if item.status in (PublicWorkoutWorkItemStatus.OPEN, PublicWorkoutWorkItemStatus.BLOCKED):
                transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.IN_PROGRESS)

    @admin.action(description='Concluir itens selecionados')
    def complete_selected(self, request, queryset):
        from .operations import transition_work_item
        for item in queryset:
            if item.status not in (PublicWorkoutWorkItemStatus.DONE, PublicWorkoutWorkItemStatus.CANCELED):
                transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.DONE)

    @admin.action(description='Bloquear itens selecionados')
    def block_selected(self, request, queryset):
        from .operations import transition_work_item
        for item in queryset:
            if item.status in (PublicWorkoutWorkItemStatus.OPEN, PublicWorkoutWorkItemStatus.IN_PROGRESS):
                transition_work_item(
                    item.pk, to_status=PublicWorkoutWorkItemStatus.BLOCKED,
                    blocked_reason='Bloqueado manualmente no admin',
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


class AwaitingNutritionFilter(admin.SimpleListFilter):
    title = 'aguardando plano nutricional'
    parameter_name = 'aguardando_nutricao'

    def lookups(self, request, model_admin):
        return (('sim', 'Sim — tier com nutrição, sem plano ativo'),)

    def queryset(self, request, queryset):
        if self.value() != 'sim':
            return queryset
        accounts_com_plano = PublicWorkoutMealPlan.objects.filter(is_active=True).values('account_id')
        return queryset.filter(
            status=PublicWorkoutSubscriptionStatus.ACTIVE,
            tier__in=['completo', 'premium'],
        ).exclude(account_id__in=accounts_com_plano)


@admin.register(PublicWorkoutAccount)
class PublicWorkoutAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'whatsapp', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at', 'updated_at', 'last_login_at', 'student_identity_id')


@admin.register(PublicWorkoutSubscription)
class PublicWorkoutSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('account', 'tier', 'status', 'plan_slug', 'custom_monthly_price', 'created_at')
    list_filter = (AwaitingActivationFilter, AwaitingNutritionFilter, 'tier', 'status')
    search_fields = ('account__email', 'plan_slug')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['generate_ai_draft', 'generate_custom_price_checkout_link']

    @admin.action(description='Gerar rascunho de treino com IA')
    def generate_ai_draft(self, request, queryset):
        from .services import generate_ai_draft_for_subscription

        for subscription in queryset:
            status, message = generate_ai_draft_for_subscription(subscription)
            level = messages.SUCCESS if status == 'success' else messages.ERROR
            self.message_user(request, f'{subscription}: {message}', level=level)

    @admin.action(description='Gerar link de checkout com valor personalizado (legado sem plano fixo)')
    def generate_custom_price_checkout_link(self, request, queryset):
        from .stripe_checkout import (
            PublicWorkoutStripeNotConfiguredError,
            start_custom_price_subscription_checkout,
        )

        success_url = request.build_absolute_uri(reverse('public-workout-account')) + '?checkout=retorno'
        cancel_url = request.build_absolute_uri(reverse('public-workout-account')) + '?checkout=cancelado'

        for subscription in queryset:
            if subscription.stripe_customer_id:
                self.message_user(
                    request,
                    f'{subscription}: já tem stripe_customer_id (já concluiu checkout antes) — '
                    'use o Customer Portal normal, não este link.',
                    level=messages.WARNING,
                )
                continue
            if subscription.custom_monthly_price is None:
                self.message_user(
                    request,
                    f'{subscription}: preencha "custom monthly price" antes de gerar o link.',
                    level=messages.ERROR,
                )
                continue
            try:
                url = start_custom_price_subscription_checkout(
                    subscription=subscription, success_url=success_url, cancel_url=cancel_url,
                )
            except PublicWorkoutStripeNotConfiguredError as exc:
                self.message_user(request, f'{subscription}: {exc}', level=messages.ERROR)
                continue
            self.message_user(
                request,
                format_html(
                    '{}: <a href="{}" target="_blank" rel="noopener">{}</a> '
                    '(copie e envie pro aluno — expira como qualquer Checkout Session da Stripe)',
                    subscription, url, url,
                ),
                level=messages.SUCCESS,
            )


@admin.register(PublicWorkoutProfessional)
class PublicWorkoutProfessionalAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'role', 'registration_council', 'registration_number',
        'weekly_capacity_minutes', 'internal_hourly_cost', 'is_active',
    )
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'registration_number')


@admin.register(PublicWorkoutWaitlistEntry)
class PublicWorkoutWaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('email', 'tier', 'status', 'created_at', 'invited_at', 'expires_at')
    list_filter = ('status', 'tier', 'created_at')
    search_fields = ('email',)
    readonly_fields = (
        'email', 'tier', 'acquisition_session', 'consented_at', 'invited_at',
        'expires_at', 'converted_at', 'created_at', 'updated_at',
    )
    actions = ('queue_invitation', 'cancel_selected')

    def has_add_permission(self, request):
        return False

    @admin.action(description='Colocar convite na fila de envio')
    def queue_invitation(self, request, queryset):
        from .outbox import TOPIC_WAITLIST_INVITE, enqueue_outbox

        queued = 0
        for entry in queryset.filter(status=PublicWorkoutWaitlistStatus.WAITING):
            enqueue_outbox(
                topic=TOPIC_WAITLIST_INVITE,
                aggregate_type='waitlist', aggregate_id=entry.pk,
                version=max(1, entry.pk),
            )
            queued += 1
        self.message_user(request, f'{queued} convite(s) colocado(s) na outbox.')

    @admin.action(description='Cancelar entradas selecionadas')
    def cancel_selected(self, request, queryset):
        count = queryset.filter(
            status__in=(PublicWorkoutWaitlistStatus.WAITING, PublicWorkoutWaitlistStatus.INVITED),
        ).update(status=PublicWorkoutWaitlistStatus.CANCELED)
        self.message_user(request, f'{count} entrada(s) cancelada(s).')


@admin.register(PublicWorkoutNutritionProfile)
class PublicWorkoutNutritionProfileAdmin(admin.ModelAdmin):
    """Leitura profissional da anamnese enviada pelo cliente.

    A equipe nao edita respostas sensiveis em nome do aluno; correcoes voltam
    pelo formulario autenticado e preservam o consentimento explicito.
    """

    list_display = ('account', 'objetivo', 'consent_health_processing_at', 'updated_at')
    search_fields = ('account__email', 'objetivo', 'comorbidades', 'alergias_restricoes')
    readonly_fields = (
        'account', 'comorbidades', 'alergias_restricoes', 'rotina_alimentar',
        'preferencias', 'objetivo', 'medicamentos', 'historico',
        'consent_health_processing_at', 'consent_version', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj) and super().has_view_permission(request, obj)


class PublicWorkoutMealPlanForm(forms.ModelForm):
    """Entrega 6, Fase 4 (D.6): payload continua sendo JSON estruturado —
    o formulario aceita a forma final como texto JSON (nao um campo por
    refeicao/item, que exigiria um formset aninhado sem lib nova — ver
    plano) e valida a mao contra nutrition_schema antes de aceitar salvar.
    Nunca aceita payload malformado, mesmo digitado direto no admin.
    """

    payload = forms.CharField(
        widget=NutritionPlanEditorWidget,
        help_text=(
            'Preencha metas, refeições, alimentos e substituições. O payload validado é gerado automaticamente.'
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
            self.message_user(
                request,
                f'{draft.slug}: aviso colocado na fila transacional de entrega.',
                level=messages.SUCCESS,
            )

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


@admin.register(PublicWorkoutProgramDelivery)
class PublicWorkoutProgramDeliveryAdmin(admin.ModelAdmin):
    list_display = ('program', 'attempt_count', 'attempted_at', 'sent_at', 'opened_at', 'last_error')
    list_filter = ('sent_at', 'opened_at')
    readonly_fields = ('program', 'attempt_count', 'attempted_at', 'sent_at', 'opened_at', 'last_error')
    actions = ['retry_delivery']

    @admin.action(description='Tentar enviar novamente')
    def retry_delivery(self, request, queryset):
        sent = 0
        for delivery in queryset.filter(sent_at__isnull=True).select_related('program'):
            if notify_program_ready(delivery.program, base_url=request.build_absolute_uri('/')):
                sent += 1
        self.message_user(request, f'{sent} aviso(s) enviado(s).')


@admin.register(PublicWorkoutMealPlanDelivery)
class PublicWorkoutMealPlanDeliveryAdmin(admin.ModelAdmin):
    list_display = ('meal_plan', 'attempt_count', 'attempted_at', 'sent_at', 'opened_at', 'last_error')
    list_filter = ('sent_at', 'opened_at')
    readonly_fields = ('meal_plan', 'attempt_count', 'attempted_at', 'sent_at', 'opened_at', 'last_error')

    def has_add_permission(self, request):
        return False


@admin.register(PublicWorkoutOutboxMessage)
class PublicWorkoutOutboxMessageAdmin(admin.ModelAdmin):
    list_display = ('topic', 'aggregate_type', 'aggregate_id', 'status', 'attempt_count', 'next_attempt_at')
    list_filter = ('status', 'topic')
    search_fields = ('idempotency_key', 'aggregate_id', 'last_error')
    readonly_fields = [field.name for field in PublicWorkoutOutboxMessage._meta.fields]
    actions = ('retry_dead_messages',)

    def has_add_permission(self, request):
        return False

    @admin.action(description='Reabrir mensagens com falha definitiva')
    def retry_dead_messages(self, request, queryset):
        count = queryset.filter(status=PublicWorkoutOutboxStatus.DEAD).update(
            status=PublicWorkoutOutboxStatus.PENDING,
            attempt_count=0,
            next_attempt_at=timezone.now(),
            last_error='',
        )
        self.message_user(request, f'{count} mensagem(ns) reaberta(s).', level=messages.SUCCESS)


@admin.register(PublicWorkoutRefundRequest)
class PublicWorkoutRefundRequestAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'payment', 'status', 'requested_at', 'processed_at', 'stripe_refund_id')
    list_filter = ('status', 'requested_at')
    search_fields = ('subscription__account__email', 'payment__stripe_invoice_id', 'stripe_refund_id')
    readonly_fields = [field.name for field in PublicWorkoutRefundRequest._meta.fields]
    actions = ('process_selected_refunds', 'reject_selected')

    def has_add_permission(self, request):
        return False

    @admin.action(description='Executar reembolso integral na Stripe')
    def process_selected_refunds(self, request, queryset):
        from .refunds import process_refund_request

        processed = 0
        for refund_request in queryset.filter(
            status__in=(PublicWorkoutRefundRequestStatus.REQUESTED, PublicWorkoutRefundRequestStatus.FAILED),
        ):
            try:
                process_refund_request(refund_request.pk)
            except Exception as exc:
                self.message_user(request, f'{refund_request}: {exc}', level=messages.ERROR)
            else:
                processed += 1
        if processed:
            self.message_user(request, f'{processed} reembolso(s) concluido(s).', level=messages.SUCCESS)

    @admin.action(description='Rejeitar pedidos selecionados')
    def reject_selected(self, request, queryset):
        count = queryset.filter(status=PublicWorkoutRefundRequestStatus.REQUESTED).update(
            status=PublicWorkoutRefundRequestStatus.REJECTED,
            processed_at=timezone.now(),
        )
        self.message_user(request, f'{count} pedido(s) rejeitado(s).')


@admin.register(PublicWorkoutTestimonial)
class PublicWorkoutTestimonialAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'account', 'consented_at', 'approved_at', 'published_at')
    list_filter = ('approved_at', 'published_at', 'consent_version')
    search_fields = ('display_name', 'quote', 'account__email')
    readonly_fields = ('created_at',)
    actions = ('approve_and_publish', 'unpublish')

    @admin.action(description='Aprovar e publicar com consentimento válido')
    def approve_and_publish(self, request, queryset):
        valid = queryset.exclude(consent_version='').filter(consented_at__isnull=False)
        count = valid.update(approved_at=timezone.now(), published_at=timezone.now())
        self.message_user(request, f'{count} depoimento(s) publicado(s).')

    @admin.action(description='Retirar da landing')
    def unpublish(self, request, queryset):
        count = queryset.update(published_at=None)
        self.message_user(request, f'{count} depoimento(s) retirado(s).')


@admin.register(PublicWorkoutMetricSnapshot)
class PublicWorkoutMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ('metric_date', 'growth_gate', 'captured_at', 'schema_version')
    list_filter = ('metric_date', 'schema_version')
    readonly_fields = [field.name for field in PublicWorkoutMetricSnapshot._meta.fields]

    @admin.display(description='Gate de crescimento')
    def growth_gate(self, obj):
        return (obj.payload or {}).get('growth_gate', {}).get('status', '—').upper()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PublicWorkoutCampaignSpend)
class PublicWorkoutCampaignSpendAdmin(admin.ModelAdmin):
    list_display = ('source', 'campaign', 'starts_on', 'ends_on', 'amount', 'currency')
    list_filter = ('source', 'currency', 'starts_on')
    search_fields = ('source', 'campaign', 'notes')
