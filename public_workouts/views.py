"""
ARQUIVO: painel interno "quem pagou e esta esperando o treino" (Curva).

POR QUE ELE EXISTE:
- A fila ja existia, mas espalhada em duas telas genericas do admin
  (AwaitingActivationFilter em PublicWorkoutSubscriptionAdmin + a lista de
  PublicWorkoutWorkItem) sem os dois lados numa unica visao. Esta tela junta
  assinatura + anamnese + rascunho + work item numa linha so, pra checar
  rapido todo dia quem esta esperando (mesmo espirito do painel de
  webhooks em integrations/views.py, que ja seguia esse padrao).

O QUE ESTE ARQUIVO FAZ:
1. Lista toda assinatura ACTIVE (pagamento confirmado) que ainda nao tem
   programa de treino publicado e/ou plano nutricional publicado.
2. Enriquece cada linha com anamnese preenchida, rascunho pendente de
   revisao e o work item correspondente (status, prazo, responsavel).

PONTOS CRITICOS:
- Acesso gated por CurvaStaffLoginRequiredMixin (staff_auth.py) — login
  PROPRIO do Curva (Renan e Giovanna), nao o sistema de papeis do OctoBox
  (access/roles/): public_workouts nao tem Box/Membership, entao nao ha'
  "owner/manager/dev" pra checar aqui.
- So leitura: nenhuma acao de estado daqui — editar continua no admin
  (PublicWorkoutWorkItemAdmin, PublicWorkoutProgramDraftAdmin) pra nao
  duplicar a logica de transicao ja validada la.
- Nao depende de PUBLIC_WORKOUT_OPERATIONS_ENABLED: a lista base vem
  direto de PublicWorkoutSubscription/PublicWorkoutProgram (sempre
  verdadeiro), o work item e so enriquecimento — se a flag estiver
  desligada em producao, a linha ainda aparece aqui (sem work item
  associado), nunca some da fila por causa da flag.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from shared_support.page_payloads import build_page_hero

from .models import (
    PublicWorkoutMealPlan,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingProfile,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from .staff_auth import SESSION_KEY, CurvaStaffLoginRequiredMixin, authenticate_staff, is_staff_authenticated

_NUTRITION_TIERS = (PublicWorkoutTier.COMPLETO, PublicWorkoutTier.PREMIUM)
_ACTIVE_WORK_ITEM_STATUSES = (
    PublicWorkoutWorkItemStatus.OPEN,
    PublicWorkoutWorkItemStatus.IN_PROGRESS,
    PublicWorkoutWorkItemStatus.BLOCKED,
)


def _safe_next_url(request):
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ) and urlparse(next_url).path:
        return next_url
    return ''


class CurvaStaffLoginView(TemplateView):
    template_name = 'public_workouts/staff_login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('next_url', _safe_next_url(self.request))
        return context

    def get(self, request, *args, **kwargs):
        if is_staff_authenticated(request):
            return redirect(_safe_next_url(request) or reverse('public-workout-activation-queue'))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        username = authenticate_staff(request.POST.get('username', ''), request.POST.get('password', ''))
        if username is None:
            return self.render_to_response(self.get_context_data(error='Usuário ou senha inválidos.'))
        request.session.cycle_key()
        request.session[SESSION_KEY] = username
        # SESSION_COOKIE_AGE global e' 30min (pensado pro admin do OctoBox
        # B2B) — curto demais pra Renan/Giovanna deixarem a fila aberta
        # trabalhando no dia. Mesmo prazo do cockpit de analytics (8h).
        request.session.set_expiry(8 * 60 * 60)
        return redirect(_safe_next_url(request) or reverse('public-workout-activation-queue'))


class CurvaStaffLogoutView(View):
    def post(self, request, *args, **kwargs):
        request.session.pop(SESSION_KEY, None)
        return redirect(reverse('public-workout-staff-login'))


class PublicWorkoutActivationQueueView(CurvaStaffLoginRequiredMixin, ListView):
    template_name = 'public_workouts/activation_queue.html'
    context_object_name = 'rows'
    paginate_by = 50

    def get_queryset(self):
        active_program_slugs = set(
            PublicWorkoutProgram.objects.filter(is_active=True).values_list('slug', flat=True)
        )
        accounts_with_meal_plan = set(
            PublicWorkoutMealPlan.objects.filter(is_active=True).values_list('account_id', flat=True)
        )

        pending = []
        subscriptions = (
            PublicWorkoutSubscription.objects.filter(status=PublicWorkoutSubscriptionStatus.ACTIVE)
            .select_related('account')
            .order_by('created_at')
        )
        for subscription in subscriptions:
            missing_training = not subscription.plan_slug or subscription.plan_slug not in active_program_slugs
            missing_nutrition = (
                subscription.tier in _NUTRITION_TIERS
                and subscription.account_id not in accounts_with_meal_plan
            )
            if missing_training or missing_nutrition:
                subscription.missing_training = missing_training
                subscription.missing_nutrition = missing_nutrition
                pending.append(subscription)
        return pending

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = list(context[self.context_object_name])
        account_ids = [row.account_id for row in rows]

        has_training_profile = set(
            PublicWorkoutTrainingProfile.objects.filter(account_id__in=account_ids).values_list(
                'account_id', flat=True,
            )
        )
        has_nutrition_profile = set(
            PublicWorkoutNutritionProfile.objects.filter(account_id__in=account_ids).values_list(
                'account_id', flat=True,
            )
        )
        pending_drafts = {}
        for draft in PublicWorkoutProgramDraft.objects.filter(
            account_id__in=account_ids, status=PublicWorkoutProgramDraftStatus.PENDING_REVIEW,
        ).order_by('created_at'):
            pending_drafts[draft.account_id] = draft

        work_items = {}
        for item in PublicWorkoutWorkItem.objects.filter(
            account_id__in=account_ids,
            item_type__in=(PublicWorkoutWorkItemType.TRAINING_PROGRAM, PublicWorkoutWorkItemType.NUTRITION_PLAN),
            status__in=_ACTIVE_WORK_ITEM_STATUSES,
        ).select_related('assigned_to').order_by('created_at'):
            work_items[(item.account_id, item.item_type)] = item

        now = timezone.now()
        for row in rows:
            row.training_profile_filled = row.account_id in has_training_profile
            row.nutrition_profile_filled = row.account_id in has_nutrition_profile
            row.pending_draft = pending_drafts.get(row.account_id)
            row.training_work_item = work_items.get((row.account_id, PublicWorkoutWorkItemType.TRAINING_PROGRAM))
            row.nutrition_work_item = work_items.get((row.account_id, PublicWorkoutWorkItemType.NUTRITION_PLAN))
            row.training_overdue = bool(row.training_work_item and row.training_work_item.due_at < now)
            row.nutrition_overdue = bool(row.nutrition_work_item and row.nutrition_work_item.due_at < now)

        context['rows'] = rows
        context['summary'] = {
            'total': len(rows),
            'missing_training': sum(1 for row in rows if row.missing_training),
            'missing_nutrition': sum(1 for row in rows if row.missing_nutrition),
            'overdue': sum(1 for row in rows if row.training_overdue or row.nutrition_overdue),
        }
        context['hero'] = build_page_hero(
            eyebrow='Curva · operação',
            title='Fila de ativação',
            copy='Quem pagou e ainda está esperando o treino ou o plano nutricional — atualizado a cada carregamento.',
            heading_level='h1',
        )
        context['staff_username'] = self.request.session.get(SESSION_KEY, '')
        return context


__all__ = ['CurvaStaffLoginView', 'CurvaStaffLogoutView', 'PublicWorkoutActivationQueueView']
