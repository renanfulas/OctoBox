"""
ARQUIVO: tela de login do corredor de treinos (/treinos/login).

POR QUE ELE EXISTE:
- Onda B1 do CORDA (docs/plans/public-workouts-produtizacao-corda.md):
  tela PROPRIA, reusando o cofre (PublicWorkoutAccount,
  PublicWorkoutLoginToken) e o gateway de e-mail — nunca a porta do
  /aluno/ (StudentSignInView em views.py), que e outro produto com outro
  fluxo (OAuth, convite de box). Arquivo separado de student_identity/views.py
  de proposito: mantem o fluxo simples de e-mail isolado da maquina de
  OAuth/convite do app de box.

PONTOS CRITICOS:
- GET sem ?token=: mostra o formulario de pedido de link.
- GET com ?token=: so mostra "Entrar como fu•••@dominio" (scanners de
  e-mail e previas de link fazem GET; nada pode ser consumido ali).
- POST action=entrar_link: consome o token e loga (seta o cookie proprio).
- POST action=entrar_codigo: o codigo de 6 digitos do mesmo e-mail, pelo
  e-mail digitado (iPhone: o link abre no Safari, fora do app instalado).
- POST sem action: emite e envia o token pro e-mail informado.
- ?next=/renan/<slug> (achado real: sem isso, o aluno tinha que voltar na
  mao pro treino depois de logar): so aceita path exato de
  /renan/<slug> — ver _safe_public_workout_next. Nao usa
  url_has_allowed_host_and_scheme do Django (que aceitaria qualquer path
  do mesmo host) de proposito: o unico destino legitimo e o proprio
  treino, entao restringir ao padrao evita qualquer superficie de
  redirecionamento aberto por construcao, nao por checagem de host.
  Viaja ate o redirect final: querystring do GET inicial -> campo hidden
  do formulario de e-mail -> dentro do link do e-mail (request_login_token)
  -> querystring do GET com ?token= -> campo hidden da confirmacao.

PublicWorkoutSubscribeView e PublicWorkoutBillingPortalView (Onda B2,
Fatia B/item 6) moram neste mesmo arquivo: precisam da mesma sessao
(cookie) que o login estabelece, e sao so POST de API (sem template
proprio ainda — a tela de assinatura e Onda B3/B4).
"""

from __future__ import annotations

import re
import json
import uuid
import logging
import hashlib

from django.contrib.auth.hashers import check_password
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View

from public_workouts import billing
from public_workouts.billing import get_or_create_subscription
from public_workouts.acquisition import (
    attach_acquisition_cookie,
    bind_acquisition_session,
    ensure_acquisition_session,
    get_acquisition_session,
    record_funnel_event,
    request_tracking_enabled,
)
from public_workouts.contracts import current_contract_versions
from public_workouts.funnel_analytics import build_acquisition_report, build_influencer_report
from public_workouts.experiments import (
    assign_active_experiments,
    build_experiment_report,
    serialize_assignments,
)
from public_workouts.capacity import get_tier_capacity
from public_workouts.journey import get_customer_journey
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutCheckoutLead,
    PublicWorkoutGuaranteeModel,
    PublicWorkoutFunnelEvent,
    PublicWorkoutNutritionProfile,
    PublicWorkoutPhysicalRestrictionTag,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutStaffCredential,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutSubscription,
    PublicWorkoutTier,
    PublicWorkoutTestimonial,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
)
from public_workouts.services import (
    NutritionIntakeValidationError,
    TrainingIntakeValidationError,
    get_training_profile,
    require_nutrition_tier,
    save_nutrition_profile,
    save_training_profile,
)

from public_workouts.stripe_checkout import (
    PublicWorkoutCheckoutSessionError,
    PublicWorkoutStripeNotConfiguredError,
    get_completed_lead_checkout,
    start_checkout_lead_session,
    start_custom_price_subscription_checkout,
    start_customer_portal_session,
    start_subscription_checkout,
)
from shared_support.security import _consume_rate_limit, _get_client_ip

logger = logging.getLogger(__name__)

from .oauth_providers import GoogleOAuthProvider, OAuthProviderError
from .public_workout_login import (
    PublicWorkoutLoginCodeAttemptsExceeded,
    PublicWorkoutLoginRateLimitExceeded,
    check_login_token,
    find_login_token,
    login_token_refusal,
    mask_login_email,
    request_login_token,
    verify_login_code_for_email,
    verify_login_token,
)
from .public_workout_oauth import build_public_workout_oauth_state, read_public_workout_oauth_state
from .public_workout_session import (
    attach_public_workout_session_cookie,
    clear_public_workout_session_cookie,
    get_public_workout_account_id_from_request,
    get_verified_public_workout_account_id_from_request,
)

_PUBLIC_WORKOUT_GOOGLE_CALLBACK_URL_NAME = 'public-workout-oauth-google-callback'


def _build_public_workout_google_provider() -> GoogleOAuthProvider:
    """GoogleOAuthProvider apontando pro callback do corredor, nunca pro
    de /aluno/ — ver oauth_providers.BaseOAuthProvider e
    public_workout_oauth.py."""
    return GoogleOAuthProvider(callback_url_name=_PUBLIC_WORKOUT_GOOGLE_CALLBACK_URL_NAME, callback_url_kwargs={})


_PUBLIC_WORKOUT_NEXT_RE = re.compile(r'^/renan/[-a-z0-9]+/?$')
# Literal exato (nao regex — sem parametro nenhum aqui), somado ao padrao de
# /renan/<slug> acima: permite que o login redirecione pra anamnese depois
# do primeiro checkout, sem abrir mao da disciplina de whitelist exata que
# o resto do arquivo ja documenta (nunca url_has_allowed_host_and_scheme,
# que aceitaria qualquer path do mesmo host).
_PUBLIC_WORKOUT_NEXT_LITERALS = ('/treinos/anamnese', '/treinos/anamnese-nutricional', '/treinos/minha-conta')


def _safe_public_workout_next(raw: str | None) -> str:
    """So aceita path exato de /renan/<slug> ou um dos literais whitelisted
    acima — string vazia pra qualquer outra coisa (ausente, absoluto com
    host, esquema `javascript:`, rota fora do corredor). Ver PONTOS
    CRITICOS no topo do arquivo."""
    candidate = (raw or '').strip()
    if candidate in _PUBLIC_WORKOUT_NEXT_LITERALS:
        return candidate
    return candidate if _PUBLIC_WORKOUT_NEXT_RE.match(candidate) else ''


def _resolve_default_next_for_account(account_id: int) -> str:
    """Quando o link de login chega SEM ?next= explicito — o caso comum de
    abrir o e-mail direto, sem ter vindo de um /renan/<slug> especifico
    nesta mesma aba — manda a pessoa direto pro proprio treino, se a conta
    ja tiver plan_slug atribuido. Achado real (usuario): sem isso, a tela
    so dizia "login feito, volte pro link do seu treino" e deixava a
    pessoa perdida.

    Nunca usa dado de request pra montar isso (por isso nao passa por
    _safe_public_workout_next) — plan_slug vem do proprio banco, resolvido
    pela conta que acabou de provar posse do e-mail, entao nao ha
    superficie de redirecionamento aberto aqui pra comecar.

    String vazia (nunca None) quando a conta ainda nao tem slug (ex.: pagou
    mas ainda esta na fila de ativacao) — nesse caso a tela de confirmacao
    "login feito" segue sendo o destino certo, nao ha treino pra mostrar
    ainda.
    """
    from public_workouts.models import PublicWorkoutProgram, PublicWorkoutSubscription

    subscription = PublicWorkoutSubscription.objects.filter(account_id=account_id).first()
    if (
        subscription is not None
        and subscription.status == PublicWorkoutSubscriptionStatus.ACTIVE
        and subscription.plan_slug
        and (
            not subscription.requires_login
            or PublicWorkoutProgram.objects.filter(slug=subscription.plan_slug, is_active=True).exists()
        )
    ):
        return f'/renan/{subscription.plan_slug}'
    return reverse('public-workout-account')


class PublicWorkoutLandingView(TemplateView):
    """GET /treinos/ — landing de vendas do corredor pra um desconhecido
    (Entrega 5, Fase 3 — D.7 do plano de escala/nutrição).

    Sem lógica de negócio: so' copy estático + os 3 CTAs de preço, cada um
    postando pra PublicWorkoutColdSignupView via JS (landing.js). Copy
    hardcoded no template Django, de proposito (D.7) — trocar uma frase
    aqui e' git commit + deploy, mais rapido que um painel de CMS que
    ninguem pediu ainda.
    """

    template_name = 'public_workouts/landing.html'
    influencer_name = ''
    influencer_code = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['funnel_tracking_enabled'] = bool(request_tracking_enabled(self.request))
        context['influencer_name'] = self.influencer_name
        context['influencer_code'] = self.influencer_code
        context['experiment_assignments'] = getattr(self, 'experiment_assignments', [])
        context['testimonials'] = PublicWorkoutTestimonial.objects.filter(
            approved_at__isnull=False, published_at__isnull=False,
        )[:6]
        professionals = PublicWorkoutProfessional.objects.filter(is_active=True).order_by('role', 'name')
        context['training_professionals'] = professionals.filter(role=PublicWorkoutProfessionalRole.TREINO)
        context['nutrition_professionals'] = professionals.filter(role=PublicWorkoutProfessionalRole.NUTRICAO)
        context['capacity_essencial'] = get_tier_capacity(PublicWorkoutTier.ESSENCIAL)
        context['capacity_completo'] = get_tier_capacity(PublicWorkoutTier.COMPLETO)
        context['capacity_premium'] = get_tier_capacity(PublicWorkoutTier.PREMIUM)
        try:
            context['invite_token'] = str(uuid.UUID(self.request.GET.get('invite') or ''))
        except ValueError:
            context['invite_token'] = ''
        return context

    def get(self, request, *args, **kwargs):
        acquisition_session, _created = ensure_acquisition_session(
            request, partner_code=self.influencer_code,
        )
        # O tráfego patrocinado é medido no painel do parceiro, fora dos
        # experimentos de conversão das campanhas próprias da Curva.
        assignments = assign_active_experiments(acquisition_session) if not self.influencer_code else []
        self.experiment_assignments = serialize_assignments(assignments)
        response = super().get(request, *args, **kwargs)
        if acquisition_session is not None:
            record_funnel_event('landing_viewed', acquisition_session=acquisition_session)
            if self.influencer_code:
                record_funnel_event(
                    'influencer_link_clicked', acquisition_session=acquisition_session,
                    partner_code=self.influencer_code,
                )
        attach_acquisition_cookie(response, acquisition_session)
        return response


class PublicWorkoutJullyLandingView(PublicWorkoutLandingView):
    """Página da Curva atribuída ao canal da Jully."""

    influencer_name = 'Jully'
    influencer_code = 'jully'


class PublicWorkoutFunnelEventView(View):
    """Eventos de interação allowlisted; nunca aceita payload comercial/PII."""

    CLIENT_EVENTS = {
        'cta_clicked', 'faq_opened', 'pricing_viewed', 'signup_started',
        'signup_submitted', 'signup_invalid', 'signup_failed', 'checkout_redirected',
    }

    def post(self, request, *args, **kwargs):
        if len(request.body) > 1024:
            return JsonResponse({'error': 'payload_invalido'}, status=400)
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning('curva_funnel_client_event_rejected reason=invalid_json')
            return JsonResponse({'error': 'payload_invalido'}, status=400)
        if not isinstance(payload, dict) or set(payload) - {'event_type', 'client_event_id', 'tier'}:
            logger.warning('curva_funnel_client_event_rejected reason=invalid_shape')
            return JsonResponse({'error': 'payload_invalido'}, status=400)
        event_type = payload.get('event_type')
        if not isinstance(event_type, str) or event_type not in self.CLIENT_EVENTS:
            logger.warning('curva_funnel_client_event_rejected reason=not_allowlisted')
            return JsonResponse({'error': 'evento_invalido'}, status=400)
        try:
            client_event_id = uuid.UUID(str(payload.get('client_event_id') or ''))
        except ValueError:
            logger.warning('curva_funnel_client_event_rejected reason=invalid_client_event_id')
            return JsonResponse({'error': 'client_event_id_invalido'}, status=400)
        session = get_acquisition_session(request)
        tier = payload.get('tier', '')
        if not isinstance(tier, str) or tier not in ('', *PublicWorkoutTier.values):
            return JsonResponse({'error': 'tier_invalido'}, status=400)
        if session is None:
            return JsonResponse({'accepted': False}, status=202)
        from shared_support.platform_cache import platform_cache
        key = f'curva:funnel:rate:{session.pk}:{int(timezone.now().timestamp()) // 60}'
        try:
            if not platform_cache.add(key, 1, timeout=120) and platform_cache.incr(key) > 60:
                return JsonResponse({'accepted': False}, status=429)
        except Exception:
            logger.warning('curva_funnel_rate_cache_unavailable')
        event = record_funnel_event(
            event_type, acquisition_session=session, client_event_id=client_event_id, tier=tier,
        )
        return JsonResponse({'accepted': event is not None}, status=202)


_ANALYTICS_SESSION_KEY = 'public_workout_analytics_username'
_ANALYTICS_DUMMY_HASH = 'pbkdf2_sha256$1200000$F5I4VTGyxIQQ3XY0S75uRN$b3g9PSCUe6l4xRuAIPCfrXqcTw6t6M162uUDTD9ZZKU='


class PublicWorkoutAnalyticsAccessMixin:
    """Mantém o cockpit Curva fora da autenticação e dos papéis do OctoBox."""

    def dispatch(self, request, *args, **kwargs):
        username = request.session.get(_ANALYTICS_SESSION_KEY, '')
        if not PublicWorkoutStaffCredential.objects.filter(username=username, is_active=True).exists():
            request.session.pop(_ANALYTICS_SESSION_KEY, None)
            return redirect('public-workout-funnel-analytics-login')
        request.analytics_username = username
        return super().dispatch(request, *args, **kwargs)


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutFunnelAnalyticsLoginView(View):
    template_name = 'public_workouts/funnel_analytics_login.html'

    def get(self, request, *args, **kwargs):
        username = request.session.get(_ANALYTICS_SESSION_KEY, '')
        if PublicWorkoutStaffCredential.objects.filter(username=username, is_active=True).exists():
            return redirect('public-workout-funnel-analytics')
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        username = (request.POST.get('username') or '').strip().lower()
        password = request.POST.get('password') or ''
        ip_token = hashlib.sha256(_get_client_ip(request).encode()).hexdigest()[:24]
        allowed, retry_after = _consume_rate_limit(
            scope='curva-analytics-login', token=ip_token, limit=10, window_seconds=300,
        )
        if not allowed:
            response = render(
                request, self.template_name,
                {'error': 'Muitas tentativas. Aguarde alguns minutos e tente novamente.',
                 'username': username, 'retry_after': retry_after},
                status=429,
            )
            response['Retry-After'] = str(retry_after)
            return response

        credential = PublicWorkoutStaffCredential.objects.filter(username=username, is_active=True).first()
        encoded_password = credential.password_hash if credential else _ANALYTICS_DUMMY_HASH
        password_matches = check_password(password, encoded_password)
        if credential is None or not password_matches:
            return render(
                request, self.template_name,
                {'error': 'Usuário ou senha inválidos.', 'username': username},
                status=401,
            )

        request.session.cycle_key()
        request.session[_ANALYTICS_SESSION_KEY] = credential.username
        request.session.set_expiry(8 * 60 * 60)
        credential.last_login_at = timezone.now()
        credential.save(update_fields=['last_login_at', 'updated_at'])
        return redirect('public-workout-funnel-analytics')


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutFunnelAnalyticsLogoutView(View):
    def post(self, request, *args, **kwargs):
        request.session.pop(_ANALYTICS_SESSION_KEY, None)
        request.session.cycle_key()
        return redirect('public-workout-funnel-analytics-login')


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutFunnelAnalyticsView(PublicWorkoutAnalyticsAccessMixin, TemplateView):
    """Cockpit comercial standalone do produto Curva."""

    template_name = 'public_workouts/funnel_analytics.html'

    def get_report(self):
        raw_days = self.request.GET.get('days', '30')
        days = int(raw_days) if raw_days in ('7', '30', '90') else 30
        report = build_acquisition_report(window_days=days)
        report['experiments'] = build_experiment_report(window_days=days)['experiments']
        from public_workouts.training_analytics import recent_training_sessions, training_summary
        summary = training_summary(window_days=days)
        report['training'] = {
            'sessions_started': summary['sessions_started'],
            'sessions_completed': summary['sessions_completed'],
            'sessions_partial': summary['sessions_partial'],
            'sessions_cancelled': summary['sessions_cancelled'],
            'sessions_abandoned': summary['sessions_abandoned'],
            'completion_rate': summary['completion_percent'],
            'sets_completed': summary['sets_completed'],
            'sets_partial': summary['sets_partial'],
            'window_days': summary['window_days'],
        }
        raw_account = self.request.GET.get('account_id', '')
        account_id = int(raw_account) if raw_account.isdigit() else None
        report['training_account_filter'] = account_id
        report['training_recent'] = recent_training_sessions(window_days=days, account_id=account_id)
        return report

    def get(self, request, *args, **kwargs):
        report = self.get_report()
        if request.GET.get('format') == 'json':
            return JsonResponse(report)
        return self.render_to_response(self.get_context_data(
            report=report, analytics_username=request.analytics_username,
        ))


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutJullyAnalyticsView(PublicWorkoutAnalyticsAccessMixin, TemplateView):
    """Painel autenticado com dados exclusivos da parceria da Jully."""

    template_name = 'public_workouts/influencer_analytics.html'

    def get(self, request, *args, **kwargs):
        raw_days = request.GET.get('days', '30')
        days = int(raw_days) if raw_days in ('7', '30', '90') else 30
        report = build_influencer_report(partner_code='jully', window_days=days)
        if request.GET.get('format') == 'json':
            return JsonResponse(report)
        return self.render_to_response(self.get_context_data(
            report=report, analytics_username=request.analytics_username,
        ))


class PublicWorkoutTermsView(TemplateView):
    template_name = 'public_workouts/terms.html'


class PublicWorkoutPrivacyView(TemplateView):
    template_name = 'public_workouts/privacy.html'


@method_decorator(never_cache, name='dispatch')
class PublicWorkoutLoginView(View):
    """GET mostra o formulário ou, com ?token=, a confirmação; só o POST entra.

    Scanners de e-mail e prévias de link (WhatsApp, Outlook) abrem o link
    antes do aluno. Quando o GET consumia o token, o aluno chegava num link
    já usado. O campo `action` separa os POSTs: entrar pelo link, entrar pelo
    código, reenviar o link de um token vencido; sem `action`, pede link.
    """

    template_name = 'treinos/login.html'

    def get(self, request, *args, **kwargs):
        token = (request.GET.get('token') or '').strip()
        next_url = _safe_public_workout_next(request.GET.get('next'))
        if not token:
            return render(request, self.template_name, {
                'next_url': next_url,
                'checkout_return': request.GET.get('checkout') == 'retorno',
            })

        login_token = find_login_token(token)
        if (login_token is not None
                and get_verified_public_workout_account_id_from_request(request) == login_token.account_id):
            # Segundo toque no mesmo e-mail, já logado neste navegador: entra
            # direto, sem gastar o token.
            return redirect(next_url or _resolve_default_next_for_account(login_token.account_id))
        reason = check_login_token(login_token)
        if reason:
            return self._render_link_refused(request, login_token, reason, next_url)
        return render(request, self.template_name, {
            'confirm_token': str(login_token.token),
            'confirm_as': mask_login_email(login_token.account.email),
            'next_url': next_url,
        })

    def post(self, request, *args, **kwargs):
        next_url = _safe_public_workout_next(request.POST.get('next'))
        action = request.POST.get('action')
        if action == 'entrar_link':
            return self._enter_with_link(request, next_url)
        if action == 'entrar_codigo':
            return self._enter_with_code(request, next_url)
        if action == 'reenviar_link':
            return self._resend_link(request, next_url)
        return self._send_link(request, next_url)

    def _logged_in(self, request, account, next_url):
        effective_next = next_url or _resolve_default_next_for_account(account.id)
        if effective_next:
            response = redirect(effective_next)
        else:
            response = render(request, self.template_name, {'logged_in_as': account.email})
        attach_public_workout_session_cookie(response, account_id=account.id, identity_verified=True)
        return response

    def _render_link_refused(self, request, login_token, reason, next_url):
        if reason == 'pagamento_pendente':
            return render(request, self.template_name, {'error': 'pagamento_pendente', 'next_url': next_url})
        context = {'error': 'link_invalido', 'next_url': next_url}
        if login_token is not None:
            # Quem tem o link vencido recebe outro no mesmo e-mail, sem digitá-lo.
            context['resend_token'] = str(login_token.token)
            context['resend_to'] = mask_login_email(login_token.account.email)
        return render(request, self.template_name, context)

    def _enter_with_link(self, request, next_url):
        token = (request.POST.get('token') or '').strip()
        account = verify_login_token(token=token)
        if account is None:
            login_token = find_login_token(token)
            return self._render_link_refused(request, login_token, login_token_refusal(login_token), next_url)
        return self._logged_in(request, account, next_url)

    def _enter_with_code(self, request, next_url):
        email = (request.POST.get('email') or '').strip().lower()
        token = (request.POST.get('token') or '').strip()
        context = {'code_form': True, 'code_email': email, 'next_url': next_url}
        if not email and token:
            # Veio do reenvio pelo link vencido: o e-mail nunca foi para a página.
            login_token = find_login_token(token)
            email = login_token.account.email if login_token is not None else ''
            context.update(code_email='', code_token=token)
        try:
            account = verify_login_code_for_email(
                email=email, code=request.POST.get('code'), client_ip=_get_client_ip(request),
            )
        except PublicWorkoutLoginCodeAttemptsExceeded:
            return render(request, self.template_name, {**context, 'error': 'muitas_tentativas'})
        if account is None:
            return render(request, self.template_name, {**context, 'error': 'codigo_invalido'})
        return self._logged_in(request, account, next_url)

    def _resend_link(self, request, next_url):
        login_token = find_login_token((request.POST.get('token') or '').strip())
        if login_token is None:
            return render(request, self.template_name, {'error': 'link_invalido', 'next_url': next_url})
        try:
            new_token = request_login_token(
                email=login_token.account.email, base_url=request.build_absolute_uri('/'), next_url=next_url,
            )
        except PublicWorkoutLoginRateLimitExceeded:
            return render(request, self.template_name, {'error': 'muitos_pedidos', 'next_url': next_url})
        if new_token is None:
            return render(request, self.template_name, {'error': 'conta_nao_ativa', 'next_url': next_url})
        return render(request, self.template_name, {
            'sent_to': mask_login_email(login_token.account.email),
            'code_form': True, 'code_token': str(login_token.token), 'next_url': next_url,
        })

    def _send_link(self, request, next_url):
        email = (request.POST.get('email') or '').strip().lower()
        if not email or '@' not in email:
            return render(request, self.template_name, {'error': 'email_invalido', 'next_url': next_url})

        try:
            token = request_login_token(email=email, base_url=request.build_absolute_uri('/'), next_url=next_url)
        except PublicWorkoutLoginRateLimitExceeded:
            return render(request, self.template_name, {'error': 'muitos_pedidos', 'next_url': next_url})

        if token is None:
            return render(request, self.template_name, {
                'error': 'conta_nao_ativa', 'next_url': next_url,
            })
        return render(request, self.template_name, {
            'sent_to': email, 'code_form': True, 'code_email': email, 'next_url': next_url,
        })


class PublicWorkoutGoogleStartView(View):
    """GET /treinos/login/google — inicia o login social do corredor.

    Reusa GoogleOAuthProvider (oauth_providers.py) como SERVICO: e o
    mesmo codigo que fala com a API do Google para o /aluno/, so que
    configurado pra redirecionar de volta pro callback do corredor (ver
    _build_public_workout_google_provider), nunca pro
    StudentOAuthCallbackView. `state` carrega o `next_url` assinado
    (public_workout_oauth.py) — nunca request.session.
    """

    def get(self, request, *args, **kwargs):
        next_url = _safe_public_workout_next(request.GET.get('next'))
        try:
            authorize_url = _build_public_workout_google_provider().get_authorize_url(
                state=build_public_workout_oauth_state(next_url=next_url),
                request=request,
            )
        except OAuthProviderError:
            return redirect(f"{reverse('public-workout-login')}?error=google_indisponivel")
        return redirect(authorize_url)


class PublicWorkoutGoogleCallbackView(View):
    """GET /treinos/login/google/callback — troca o `code` do Google pelo
    e-mail e loga.

    Espelha o POST de confirmacao de PublicWorkoutLoginView: consome uma
    prova de identidade de uso unico (aqui, code+state do Google,
    validados pelo proprio Google e pela assinatura do state) e seta o
    mesmo cookie do corredor. A identidade Google autentica, mas nunca
    cria a conta de um lead ou de um email sem pagamento confirmado.
    """

    template_name = 'treinos/login.html'

    def get(self, request, *args, **kwargs):
        state_payload = read_public_workout_oauth_state(request.GET.get('state', ''))
        next_url = _safe_public_workout_next((state_payload or {}).get('next_url', ''))
        code = (request.GET.get('code') or '').strip()
        if state_payload is None or not code:
            return render(request, self.template_name, {'error': 'link_invalido', 'next_url': next_url})

        try:
            identity = _build_public_workout_google_provider().exchange_code(code=code, request=request)
        except OAuthProviderError:
            return render(request, self.template_name, {'error': 'google_falhou', 'next_url': next_url})

        account = PublicWorkoutAccount.objects.filter(email__iexact=identity.email).first()
        if account is None:
            return render(request, self.template_name, {'error': 'conta_nao_encontrada'})
        subscription = getattr(account, 'subscription', None)
        if (subscription is not None and subscription.requires_login
                and subscription.status == PublicWorkoutSubscriptionStatus.PENDING_PAYMENT):
            return render(request, self.template_name, {'error': 'pagamento_pendente'})
        if identity.photo_url and account.photo_url != identity.photo_url:
            account.photo_url = identity.photo_url
        account.last_login_at = timezone.now()
        account.save(update_fields=['last_login_at', 'updated_at'])

        if next_url:
            response = redirect(next_url)
        else:
            response = render(request, self.template_name, {'logged_in_as': account.email})
        attach_public_workout_session_cookie(response, account_id=account.id, identity_verified=True)
        return response


class PublicWorkoutSubscribeView(View):
    """POST /treinos/subscribe — inicia o checkout da assinatura (Onda B2, Fatia B).

    Exige o cookie do corredor (aluno ja logado — mesmo mecanismo do login
    acima). Sem template proprio: devolve JSON com a URL hospedada da
    Stripe, a tela de assinatura fica pra B3/B4.
    """

    def post(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        try:
            account = PublicWorkoutAccount.objects.get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        plan_slug = (request.POST.get('plan_slug') or '').strip()
        if not plan_slug:
            return JsonResponse({'error': 'plan_slug_obrigatorio'}, status=400)

        # Fluxo legado (aluno ja onboardado manualmente por Renan): sempre
        # ESSENCIAL, unico tier que existia antes da Entrega 5. Escolha de
        # tier por quem assina de verdade so existe no cadastro a frio
        # (PublicWorkoutColdSignupView, abaixo).
        subscription = get_or_create_subscription(
            account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug=plan_slug
        )

        login_url = request.build_absolute_uri(reverse('public-workout-login'))
        try:
            checkout_url = start_subscription_checkout(
                subscription=subscription,
                success_url=f'{login_url}?assinatura=sucesso',
                cancel_url=f'{login_url}?assinatura=cancelada',
            )
        except PublicWorkoutStripeNotConfiguredError as exc:
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)

        return JsonResponse({'checkout_url': checkout_url})


class PublicWorkoutColdSignupView(View):
    """POST /treinos/cadastro — inicia o checkout pra um DESCONHECIDO, sem
    cookie de sessao e sem plan_slug (Entrega 5, Fase 2 — D.1/D.2/D.2b).

    Duas travas que PublicWorkoutSubscribeView exige (cookie de sessao +
    plan_slug ja existente) nao se aplicam aqui de proposito — e exatamente
    o gap que o cadastro a frio fecha: um estranho que nunca falou com o
    Renan e nunca recebeu link de login. A assinatura nasce PENDING_PAYMENT
    (get_or_create_subscription, D.2b) — so o webhook confirma pra ACTIVE
    depois do pagamento de verdade (RT7). `plan_slug` fica None: quem
    atribui e Renan/esposa, manualmente, ao revisar a fila (D.2).
    """

    def post(self, request, *args, **kwargs):
        email = (request.POST.get('email') or '').strip().lower()
        tier = request.POST.get('tier')
        if not email or '@' not in email or tier not in PublicWorkoutTier.values:
            return JsonResponse({'error': 'email_ou_tier_invalido'}, status=400)
        if request.POST.get('accept_contract') != '1':
            return JsonResponse({'error': 'aceite_contrato_obrigatorio'}, status=400)

        acquisition_session = get_acquisition_session(request)
        # Contas com pagamento confirmado continuam pelo login. Contas antigas
        # que ficaram pendentes podem retomar o checkout sem ganhar sessão.
        account = PublicWorkoutAccount.objects.filter(email__iexact=email).first()
        account_subscription = getattr(account, 'subscription', None) if account is not None else None
        session_account_id = get_public_workout_account_id_from_request(request)
        owns_account = account is not None and session_account_id == account.pk
        if account is not None and not owns_account and (
            account_subscription is None
            or account_subscription.status != PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        ):
            record_funnel_event('login_required', acquisition_session=acquisition_session, tier=tier)
            response = JsonResponse({
                'checkout_url': request.build_absolute_uri(reverse('public-workout-login')),
                'login_required': True,
            })
            attach_acquisition_cookie(response, acquisition_session)
            return response
        if owns_account and account_subscription is not None and account_subscription.status in (
            PublicWorkoutSubscriptionStatus.ACTIVE,
            PublicWorkoutSubscriptionStatus.PAST_DUE,
            PublicWorkoutSubscriptionStatus.SUSPENDED,
        ):
            response = JsonResponse({'checkout_url': request.build_absolute_uri(reverse('public-workout-account'))})
            attach_acquisition_cookie(response, acquisition_session)
            return response

        capacity = get_tier_capacity(tier)
        invited_entry = None
        raw_invite_token = (request.POST.get('invite_token') or '').strip()
        if raw_invite_token:
            try:
                invite_uuid = uuid.UUID(raw_invite_token)
            except ValueError:
                invite_uuid = None
            if invite_uuid is not None:
                invited_entry = PublicWorkoutWaitlistEntry.objects.filter(
                    invite_token=invite_uuid,
                    email__iexact=email,
                    tier=tier,
                    status=PublicWorkoutWaitlistStatus.INVITED,
                    expires_at__gte=timezone.now(),
                ).first()
                if invited_entry is None:
                    PublicWorkoutWaitlistEntry.objects.filter(
                        invite_token=invite_uuid,
                        status=PublicWorkoutWaitlistStatus.INVITED,
                        expires_at__lt=timezone.now(),
                    ).update(status=PublicWorkoutWaitlistStatus.EXPIRED)
        if not capacity['checkout_allowed'] and invited_entry is None:
            entry, _created = PublicWorkoutWaitlistEntry.objects.get_or_create(
                email=email,
                tier=tier,
                status=PublicWorkoutWaitlistStatus.WAITING,
                defaults={'acquisition_session': acquisition_session},
            )
            if entry.acquisition_session_id is None and acquisition_session is not None:
                entry.acquisition_session = acquisition_session
                entry.save(update_fields=['acquisition_session', 'updated_at'])
            record_funnel_event(
                'waitlist_joined', acquisition_session=acquisition_session, tier=tier,
            )
            response = JsonResponse({
                'waitlisted': True,
                'message': 'Sua prioridade foi registrada. Avisaremos quando abrir uma vaga.',
            }, status=202)
            attach_acquisition_cookie(response, acquisition_session)
            return response

        contract_versions = current_contract_versions()
        if owns_account and account_subscription is not None and account_subscription.status == PublicWorkoutSubscriptionStatus.CANCELED:
            subscription = get_or_create_subscription(account=account, tier=tier)
            for field_name, value in contract_versions.items():
                setattr(subscription, field_name, value)
            subscription.guarantee_model = PublicWorkoutGuaranteeModel.REFUND_GUARANTEE
            subscription.contract_accepted_at = timezone.now()
            subscription.requires_login = True
            subscription.save(update_fields=[*contract_versions, 'guarantee_model', 'contract_accepted_at', 'requires_login', 'updated_at'])
            return_url = request.build_absolute_uri(reverse('public-workout-checkout-return'))
            try:
                checkout_url = start_subscription_checkout(
                    subscription=subscription,
                    success_url=f'{return_url}?session_id={{CHECKOUT_SESSION_ID}}',
                    cancel_url=f"{request.build_absolute_uri(reverse('public-workout-landing'))}#curva-precos",
                    acquisition_session_id=(acquisition_session.pk if acquisition_session else None),
                )
            except PublicWorkoutStripeNotConfiguredError as exc:
                return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)
            return JsonResponse({'checkout_url': checkout_url})
        marketing_consent = request.POST.get('marketing_consent') == '1'
        lead, _ = PublicWorkoutCheckoutLead.objects.get_or_create(
            email=email, paid_at__isnull=True,
            defaults={
                'tier': tier,
                'acquisition_session': acquisition_session,
                'guarantee_model': PublicWorkoutGuaranteeModel.REFUND_GUARANTEE,
                'marketing_consent': marketing_consent,
                'marketing_consent_at': timezone.now() if marketing_consent else None,
                **contract_versions,
            },
        )
        return_url = request.build_absolute_uri(reverse('public-workout-checkout-return'))
        try:
            completed_session = get_completed_lead_checkout(lead=lead)
        except PublicWorkoutStripeNotConfiguredError as exc:
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)
        except PublicWorkoutCheckoutSessionError as exc:
            return JsonResponse({'error': 'checkout_anterior_pendente', 'detail': str(exc)}, status=409)
        if completed_session is not None:
            response = JsonResponse({
                'checkout_url': f'{return_url}?session_id={completed_session.id}',
                'payment_complete': True,
            })
            attach_acquisition_cookie(response, acquisition_session)
            return response
        changed = []
        if lead.tier != tier:
            lead.tier = tier; changed.append('tier')
        if acquisition_session and not lead.acquisition_session_id:
            lead.acquisition_session = acquisition_session; changed.append('acquisition_session')
        for field_name, value in contract_versions.items():
            if getattr(lead, field_name) != value:
                setattr(lead, field_name, value); changed.append(field_name)
        if marketing_consent and not lead.marketing_consent:
            lead.marketing_consent = True
            lead.marketing_consent_at = timezone.now()
            changed.extend(['marketing_consent', 'marketing_consent_at'])
        if changed:
            lead.save(update_fields=[*changed, 'updated_at'])
        record_funnel_event('tier_selected', acquisition_session=acquisition_session, tier=tier)
        try:
            checkout_url = start_checkout_lead_session(
                lead=lead,
                success_url=f'{return_url}?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f"{request.build_absolute_uri(reverse('public-workout-landing'))}#curva-precos",
            )
        except PublicWorkoutStripeNotConfiguredError as exc:
            record_funnel_event('checkout_failed', acquisition_session=acquisition_session, tier=tier)
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)
        except PublicWorkoutCheckoutSessionError as exc:
            record_funnel_event('checkout_failed', acquisition_session=acquisition_session, tier=tier)
            return JsonResponse({'error': 'checkout_anterior_pendente', 'detail': str(exc)}, status=409)

        record_funnel_event(
            'checkout_started', acquisition_session=acquisition_session, tier=tier,
        )
        response = JsonResponse({'checkout_url': checkout_url})
        attach_acquisition_cookie(response, acquisition_session)
        return response


class PublicWorkoutCheckoutReturnView(View):
    """Verify Stripe's return server-side before creating/logging in a student."""

    def get(self, request, *args, **kwargs):
        session_id = (request.GET.get('session_id') or '').strip()
        secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
        if not session_id or not secret_key:
            return redirect(f"{reverse('public-workout-landing')}#curva-precos")
        import stripe
        stripe.api_key = secret_key
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except Exception:
            logger.exception('curva_checkout_return_session_retrieve_failed')
            return redirect(f"{reverse('public-workout-landing')}#curva-precos")
        metadata = session.get('metadata', {}) or {}
        if (metadata.get('product') != 'coaching' or session.get('status') != 'complete'
                or session.get('payment_status') != 'paid'):
            return redirect(f"{reverse('public-workout-landing')}#curva-precos")
        lead_id = metadata.get('public_workout_checkout_lead_id')
        if lead_id:
            lead = PublicWorkoutCheckoutLead.objects.filter(
                pk=lead_id, stripe_checkout_session_id=session_id,
                tier=metadata.get('tier'),
            ).first()
            if lead is None:
                return redirect(f"{reverse('public-workout-landing')}#curva-precos")
            subscription = billing.provision_paid_checkout_lead(
                lead.pk, customer_id=session.get('customer') or '',
                stripe_subscription_id=session.get('subscription') or '',
            )
            account = subscription.account
        else:
            local_id = metadata.get('public_workout_subscription_id')
            subscription = PublicWorkoutSubscription.objects.filter(pk=local_id).first()
            if subscription is None:
                return redirect(f"{reverse('public-workout-landing')}#curva-precos")
            account = subscription.account
        # Checkout proves payment, but the address typed into checkout is not
        # proof of mailbox ownership. Require the normal email magic link
        # before issuing an authenticated session.
        account_id = get_public_workout_account_id_from_request(request)
        if account_id == account.pk:
            return redirect(f"{reverse('public-workout-account')}?checkout=retorno")
        return redirect(f"{reverse('public-workout-login')}?checkout=retorno")


class PublicWorkoutCustomCheckoutView(View):
    """POST /treinos/checkout-personalizado — self-service do checkout de
    valor negociado, pra cliente legado ACTIVE que nunca passou pela
    Stripe (achado real: Rafael — seed_legacy_workout_accounts cria a
    assinatura ja' ACTIVE, status que get_customer_journey() nunca trata
    como "precisa pagar", entao /treinos/minha-conta nao mostrava nada
    sobre pagamento e "Pagamentos" caia num link morto).

    Antes desta view, o UNICO jeito de gerar esse checkout era a acao de
    admin "Gerar link de checkout com valor personalizado" (Public
    Workout Subscription, PublicWorkoutSubscriptionAdmin) -- o Renan
    tinha que copiar a URL e mandar por fora (WhatsApp). Esta view fecha
    o loop DENTRO do app, mas so' funciona depois que ele ja' preencheu
    `custom_monthly_price` no admin pra aquela assinatura -- nunca aceita
    valor vindo do proprio request (mesma trava de
    start_custom_price_subscription_checkout). Sem o valor definido:
    404 'valor_nao_definido' -- o template mostra "Fale com o Renan" em
    vez de um botao que sempre falharia.
    """

    def post(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        try:
            account = PublicWorkoutAccount.objects.get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        subscription = getattr(account, 'subscription', None)
        if subscription is None or subscription.stripe_customer_id:
            # Sem assinatura, ou ja tem stripe_customer_id (usa o Customer
            # Portal normal, data-billing-portal) -- este caminho nao se
            # aplica, nao e erro de configuracao.
            return JsonResponse({'error': 'nao_aplicavel'}, status=404)
        if subscription.custom_monthly_price is None:
            return JsonResponse({'error': 'valor_nao_definido'}, status=404)

        account_url = request.build_absolute_uri(reverse('public-workout-account'))
        try:
            checkout_url = start_custom_price_subscription_checkout(
                subscription=subscription,
                success_url=f'{account_url}?checkout=retorno',
                cancel_url=f'{account_url}?checkout=cancelado',
            )
        except PublicWorkoutStripeNotConfiguredError as exc:
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)

        return JsonResponse({'checkout_url': checkout_url})


class PublicWorkoutBillingPortalView(View):
    """POST /treinos/billing-portal — abre o Portal do Cliente Stripe pra
    o aluno gerenciar/cancelar a propria assinatura sozinho (Onda B2,
    item 6 — ultimo item da onda, o Customer Portal nunca tinha sido
    implementado; so existia uma mencao a ele como possibilidade futura
    no docstring de mark_subscription_canceled).

    Mesmo mecanismo de sessao de PublicWorkoutSubscribeView. So funciona
    pra conta que ja tem `stripe_customer_id` preenchido — ou seja, ja
    concluiu 1 checkout de verdade (link_stripe_ids, via o webhook de
    checkout.session.completed). Sem isso, 404 — nao ha o que gerenciar
    ainda, nao e erro de configuracao.

    O cancelamento que o aluno faz dentro do portal da Stripe chega de
    volta pelo MESMO webhook que ja existe (`customer.subscription.deleted`
    -> mark_subscription_canceled) — esta view nunca muda o status da
    PublicWorkoutSubscription diretamente.
    """

    def post(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        try:
            account = PublicWorkoutAccount.objects.get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            return JsonResponse({'error': 'nao_autenticado'}, status=401)

        subscription = getattr(account, 'subscription', None)
        if subscription is None or not subscription.stripe_customer_id:
            return JsonResponse({'error': 'sem_assinatura_com_checkout_concluido'}, status=404)

        return_url = request.build_absolute_uri(reverse('public-workout-account'))
        try:
            portal_url = start_customer_portal_session(
                customer_id=subscription.stripe_customer_id, return_url=return_url
            )
        except PublicWorkoutStripeNotConfiguredError as exc:
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)

        return JsonResponse({'portal_url': portal_url})


class PublicWorkoutTrainingIntakeView(View):
    """GET/POST /treinos/anamnese — anamnese de treino (D4 do plano de
    produto: "tudo que alimenta a IA comeca a coletar antes da IA existir").

    Pagina HTML server-rendered, nao endpoint JSON (diferente das outras
    views deste arquivo): sem sessao ativa, redireciona pro login com
    ?next=/treinos/anamnese em vez de devolver 401 — o aluno chega aqui
    clicando num link, nao via fetch() de JS.

    Toda validacao de verdade (consentimento obrigatorio, valores de
    escolha validos) mora em services.save_training_profile — esta view so'
    traduz POST em kwargs e trata TrainingIntakeValidationError como erro
    de formulario re-renderizado, nunca 500.
    """

    template_name = 'treinos/anamnese.html'

    def _form_context(self, account_id: int) -> dict:
        return {
            'goals': PublicWorkoutTrainingGoal.choices,
            'experiences': PublicWorkoutTrainingExperience.choices,
            'locations': PublicWorkoutTrainingLocation.choices,
            'restriction_tags': PublicWorkoutPhysicalRestrictionTag.choices,
            'profile': get_training_profile(account_id=account_id),
        }

    def get(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return redirect(f"{reverse('public-workout-login')}?next=/treinos/anamnese")
        return render(request, self.template_name, self._form_context(account_id))

    def post(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return redirect(f"{reverse('public-workout-login')}?next=/treinos/anamnese")

        try:
            raw_days = int(request.POST.get('days_per_week') or 0)
        except ValueError:
            raw_days = 0

        try:
            save_training_profile(
                account_id=account_id,
                goal=request.POST.get('goal') or '',
                physical_restrictions=request.POST.getlist('physical_restrictions'),
                physical_restrictions_detail=(request.POST.get('physical_restrictions_detail') or '').strip(),
                training_experience=request.POST.get('training_experience') or '',
                days_per_week=raw_days,
                training_location=request.POST.get('training_location') or '',
                motivation=(request.POST.get('motivation') or '').strip(),
                biggest_difficulty=(request.POST.get('biggest_difficulty') or '').strip(),
                consent_given=request.POST.get('consent') == 'on',
            )
        except TrainingIntakeValidationError as exc:
            context = self._form_context(account_id)
            context['error'] = str(exc)
            return render(request, self.template_name, context, status=400)

        from public_workouts.operations import ensure_required_work_items
        account = PublicWorkoutAccount.objects.get(pk=account_id)
        subscription = getattr(account, 'subscription', None)
        # Compatibilidade B0: contas legadas podiam preencher anamnese antes
        # de existir assinatura. Persistir o perfil continua valido; a fila
        # operacional nasce quando uma assinatura ativa for reconciliada.
        if subscription is not None:
            ensure_required_work_items(subscription.pk)
            record_funnel_event(
                'training_intake_completed', account=subscription.account,
                subscription=subscription, tier=subscription.tier,
            )

        return redirect(f"{reverse('public-workout-account')}?anamnese=salva")


class PublicWorkoutAccountView(View):
    """Hub autenticado que traduz o estado tecnico em proximo passo."""

    template_name = 'treinos/minha_conta.html'

    def get(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return redirect(f"{reverse('public-workout-login')}?next=/treinos/minha-conta")
        try:
            account = PublicWorkoutAccount.objects.select_related(
                'subscription', 'training_profile', 'nutrition_profile'
            ).get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            response = redirect('public-workout-login')
            return clear_public_workout_session_cookie(response)

        journey = get_customer_journey(account)
        checkout_canceled = request.GET.get('checkout') == 'cancelado'
        if checkout_canceled:
            subscription = getattr(account, 'subscription', None)
            acquisition_session = get_acquisition_session(request)
            if not PublicWorkoutFunnelEvent.objects.filter(
                event_type='checkout_canceled', acquisition_session=acquisition_session,
                subscription=subscription,
            ).exists():
                record_funnel_event(
                    'checkout_canceled', account=account, subscription=subscription,
                    tier=getattr(subscription, 'tier', ''),
                    acquisition_session=acquisition_session,
                )
        from public_workouts.refunds import get_refund_eligibility
        refund = get_refund_eligibility(account.subscription) if hasattr(account, 'subscription') else None
        if request.GET.get('format') == 'json':
            return JsonResponse(journey.as_dict())
        return render(request, self.template_name, {
            'account': account,
            'journey': journey,
            'checkout_returned': request.GET.get('checkout') == 'retorno',
            'checkout_canceled': checkout_canceled,
            'intake_saved': request.GET.get('anamnese') == 'salva',
            'refund': refund,
            'refund_requested': request.GET.get('garantia') == 'solicitada',
        })


class PublicWorkoutRefundRequestView(View):
    def post(self, request, *args, **kwargs):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return redirect(f"{reverse('public-workout-login')}?next=/treinos/minha-conta")
        try:
            account = PublicWorkoutAccount.objects.select_related('subscription').get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            return redirect('public-workout-login')
        from public_workouts.refunds import RefundNotEligibleError, submit_refund_request
        try:
            submit_refund_request(
                subscription=account.subscription,
                reason=(request.POST.get('reason') or '').strip(),
            )
        except RefundNotEligibleError as exc:
            return JsonResponse({'error': 'garantia_indisponivel', 'detail': str(exc)}, status=409)
        return redirect(f"{reverse('public-workout-account')}?garantia=solicitada")


class PublicWorkoutNutritionIntakeView(View):
    template_name = 'treinos/anamnese_nutricional.html'

    def _resolve_account(self, request):
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return None
        try:
            account = PublicWorkoutAccount.objects.select_related('subscription', 'nutrition_profile').get(pk=account_id)
        except PublicWorkoutAccount.DoesNotExist:
            return None
        subscription = getattr(account, 'subscription', None)
        if (
            subscription is None
            or subscription.status != PublicWorkoutSubscriptionStatus.ACTIVE
            or not require_nutrition_tier(subscription)
        ):
            return None
        return account

    def get(self, request, *args, **kwargs):
        account = self._resolve_account(request)
        if account is None:
            return redirect(f"{reverse('public-workout-account')}")
        return render(request, self.template_name, {'profile': getattr(account, 'nutrition_profile', None)})

    def post(self, request, *args, **kwargs):
        account = self._resolve_account(request)
        if account is None:
            return redirect(reverse('public-workout-account'))
        try:
            save_nutrition_profile(
                account_id=account.pk,
                comorbidades=request.POST.get('comorbidades') or '',
                alergias_restricoes=request.POST.get('alergias_restricoes') or '',
                rotina_alimentar=request.POST.get('rotina_alimentar') or '',
                preferencias=request.POST.get('preferencias') or '',
                objetivo=request.POST.get('objetivo') or '',
                medicamentos=request.POST.get('medicamentos') or '',
                historico=request.POST.get('historico') or '',
                consent_given=request.POST.get('consent') == 'on',
            )
        except NutritionIntakeValidationError as exc:
            return render(request, self.template_name, {
                'profile': getattr(account, 'nutrition_profile', None), 'error': str(exc),
            }, status=400)

        from public_workouts.operations import ensure_required_work_items
        ensure_required_work_items(account.subscription.pk)
        record_funnel_event(
            'nutrition_intake_completed', account=account,
            subscription=account.subscription, tier=account.subscription.tier,
        )
        return redirect(f"{reverse('public-workout-account')}?anamnese=salva")


class PublicWorkoutAccountSignOutView(View):
    def post(self, request, *args, **kwargs):
        response = redirect('public-workout-landing')
        return clear_public_workout_session_cookie(response)
