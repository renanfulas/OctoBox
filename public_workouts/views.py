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

from datetime import timedelta
from urllib.parse import quote, urlparse

from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from shared_support.page_payloads import build_page_hero

from .models import (
    PublicWorkoutAccount,
    PublicWorkoutLoadLog,
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


def _build_checkin_whatsapp_url(*, phone: str, student_label: str) -> str | None:
    """Link wa.me pra 'chamar aluno' (achado do Renan: saber se esta tudo
    bem). `phone` ja' vem normalizado (so digitos) por
    PublicWorkoutAccount.save() -- None quando o campo esta vazio, o
    template decide o que mostrar no lugar (nunca inventa numero)."""
    if not phone:
        return None
    message = f'Oi {student_label}! Passando aqui pra saber como você está — tudo bem com o treino?'
    return f'https://wa.me/{phone}?text={quote(message)}'


class CoachStudentRosterView(CurvaStaffLoginRequiredMixin, ListView):
    """Painel do treinador: evolução dos alunos numa tela só (achado do
    Renan — "saber a evolução de forma fácil, a data que foi o treino").

    So leitura, mesmo espirito de PublicWorkoutActivationQueueView: editar
    o programa de verdade continua no admin/ficha do aluno (modificação
    pontual reaproveita generate_ai_draft_for_subscription, nunca um editor
    novo de exercicio/serie aqui)."""

    template_name = 'public_workouts/coach_roster.html'
    context_object_name = 'rows'

    def get_queryset(self):
        return (
            PublicWorkoutSubscription.objects.exclude(status=PublicWorkoutSubscriptionStatus.CANCELED)
            .select_related('account')
            .order_by('account__email')
        )

    def get_context_data(self, **kwargs):
        from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

        from .risk_signals import compute_student_risk
        from .services import build_weekly_review

        context = super().get_context_data(**kwargs)
        rows = list(context[self.context_object_name])
        account_ids = [row.account_id for row in rows]

        last_workout_by_account = dict(
            PublicWorkoutLoadLog.objects.filter(account_id__in=account_ids, is_active=True)
            .values('account_id').annotate(last=Max('performed_on')).values_list('account_id', 'last')
        )
        week_ago = timezone.localdate() - timedelta(days=7)
        sessions_this_week_by_account: dict[int, set] = {}
        for account_id, performed_on in (
            PublicWorkoutLoadLog.objects.filter(
                account_id__in=account_ids, is_active=True, performed_on__gte=week_ago,
            ).values_list('account_id', 'performed_on').distinct()
        ):
            sessions_this_week_by_account.setdefault(account_id, set()).add(performed_on)

        today = timezone.localdate()
        for row in rows:
            plan = PUBLIC_WORKOUT_LIBRARY.get(row.plan_slug or '')
            row.student_label = plan.short_name if plan else row.account.email
            last_workout_on = last_workout_by_account.get(row.account_id)
            row.last_workout_on = last_workout_on
            row.days_since_last_workout = (today - last_workout_on).days if last_workout_on else None
            row.sessions_this_week = len(sessions_this_week_by_account.get(row.account_id, ()))
            row.whatsapp_url = _build_checkin_whatsapp_url(
                phone=row.account.whatsapp, student_label=row.student_label,
            )
            # Sinal de progresso: uma chamada por aluno (~10-15 alunos reais
            # hoje, ver docstring de risk_signals.py) -- bulk-agregar isso
            # exigiria reimplementar build_weekly_review pra N contas de
            # uma vez; nao vale a complexidade nesta escala ainda.
            weekly_review = build_weekly_review(account_id=row.account_id)
            row.days_until_renewal = (
                (row.current_period_end.date() - today).days if row.current_period_end else None
            )
            risk = compute_student_risk(
                days_since_last_workout=row.days_since_last_workout,
                declining_movements=weekly_review['declining_movements'],
                plateaued_movements=weekly_review['plateaued_movements'],
                tracked_movement_count=len(weekly_review['trends_by_movement']),
                subscription_status=row.status,
                days_until_renewal=row.days_until_renewal,
            )
            row.risk_level = risk.level
            row.risk_reasons = risk.reasons

        # Risco primeiro (quem precisa de acao aparece no topo), depois
        # quem esta ha mais tempo sumido dentro do mesmo nivel -- nunca
        # ordem alfabetica de e-mail pra ISSO, so' pra fila plana abaixo
        # dela fazer sentido visual (a ordem alfabetica original vem do
        # get_queryset, mantida como fallback estavel de desempate).
        risk_order = {'high': 0, 'medium': 1, 'healthy': 2}
        rows.sort(key=lambda row: (
            risk_order[row.risk_level],
            -(row.days_since_last_workout if row.days_since_last_workout is not None else 9999),
        ))

        context['rows'] = rows
        context['high_risk_rows'] = [row for row in rows if row.risk_level == 'high']
        context['medium_risk_rows'] = [row for row in rows if row.risk_level == 'medium']
        context['risk_summary'] = {
            'high': len(context['high_risk_rows']),
            'medium': len(context['medium_risk_rows']),
            'healthy': sum(1 for row in rows if row.risk_level == 'healthy'),
            'renewing_soon': sum(
                1 for row in rows
                if row.days_until_renewal is not None and 0 <= row.days_until_renewal <= 7
            ),
        }
        context['hero'] = build_page_hero(
            eyebrow='Curva · alunos',
            title='Evolução dos alunos',
            copy='Quem treinou, quando, e quem pode estar sumindo — tudo numa tela só.',
            heading_level='h1',
        )
        context['staff_username'] = self.request.session.get(SESSION_KEY, '')
        return context


class CoachStudentDetailView(CurvaStaffLoginRequiredMixin, View):
    """Ficha do aluno: evolução por movimento, versões do programa e as
    duas ações pedidas — chamar no WhatsApp e gerar novo rascunho de
    treino (reaproveita o MESMO fluxo do admin, nunca edição manual linha
    a linha — decisão explícita do Renan)."""

    template_name = 'public_workouts/coach_student_detail.html'

    def _build_context(self, account, *, notice=None):
        from public_workouts.progress_snapshot import build_progress_snapshots
        from public_workouts.templatetags.public_workouts_extras import load_chart_points
        from student_app.views.public_workout_views import PUBLIC_WORKOUT_LIBRARY

        from .services import build_movement_label_lookup, get_active_program, list_load_history, list_program_versions

        subscription = getattr(account, 'subscription', None)
        plan_slug = subscription.plan_slug if subscription else ''
        plan = PUBLIC_WORKOUT_LIBRARY.get(plan_slug or '')
        program = get_active_program(slug=plan_slug) if plan_slug else None
        movement_labels = build_movement_label_lookup(program) if program else {}

        load_history = list_load_history(account_id=account.pk, only_active=True)
        by_movement: dict[str, list] = {}
        for entry in load_history:
            by_movement.setdefault(entry['movement_slug'], []).append(entry)

        progress_snapshots = build_progress_snapshots(account_id=account.pk)
        charts = []
        for movement_slug, entries in by_movement.items():
            snapshot = progress_snapshots.get(movement_slug)
            charts.append({
                'slug': movement_slug,
                'label': movement_labels.get(movement_slug, movement_slug),
                'chart': load_chart_points(entries),
                'trend_signal': snapshot.trend_signal if snapshot else 'insufficient_data',
            })
        charts.sort(key=lambda item: item['label'])

        pending_draft = None
        if plan_slug:
            pending_draft = PublicWorkoutProgramDraft.objects.filter(
                account=account, slug=plan_slug, status=PublicWorkoutProgramDraftStatus.PENDING_REVIEW,
            ).first()

        return {
            'account': account,
            'subscription': subscription,
            'student_label': plan.short_name if plan else account.email,
            'plan_slug': plan_slug,
            'program_versions': list_program_versions(slug=plan_slug) if plan_slug else [],
            'charts': charts,
            'load_history': load_history,
            'pending_draft': pending_draft,
            'whatsapp_url': _build_checkin_whatsapp_url(
                phone=account.whatsapp, student_label=plan.short_name if plan else account.email,
            ),
            'notice': notice,
            'staff_username': self.request.session.get(SESSION_KEY, ''),
        }

    def get(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(PublicWorkoutAccount, pk=account_id)
        notice = None
        draft_status = request.GET.get('rascunho')
        if draft_status:
            notice = {'status': draft_status, 'message': request.GET.get('mensagem', '')}
        return render(request, self.template_name, self._build_context(account, notice=notice))

    def post(self, request, account_id, *args, **kwargs):
        from .services import generate_ai_draft_for_subscription

        account = get_object_or_404(PublicWorkoutAccount, pk=account_id)
        subscription = getattr(account, 'subscription', None)
        if subscription is None:
            status, message = 'error', 'aluno sem assinatura — nada pra gerar.'
        else:
            status, message = generate_ai_draft_for_subscription(subscription)
        detail_url = reverse('public-workout-coach-student-detail', kwargs={'account_id': account_id})
        return redirect(f'{detail_url}?rascunho={status}&mensagem={quote(message)}')


__all__ = [
    'CoachStudentDetailView', 'CoachStudentRosterView', 'CurvaStaffLoginView', 'CurvaStaffLogoutView',
    'PublicWorkoutActivationQueueView',
]
