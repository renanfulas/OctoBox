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
- GET com ?token=: consome o token e loga (seta o cookie proprio).
- POST: emite e envia o token pro e-mail informado.
- ?next=/renan/<slug> (achado real: sem isso, o aluno tinha que voltar na
  mao pro treino depois de logar): so aceita path exato de
  /renan/<slug> — ver _safe_public_workout_next. Nao usa
  url_has_allowed_host_and_scheme do Django (que aceitaria qualquer path
  do mesmo host) de proposito: o unico destino legitimo e o proprio
  treino, entao restringir ao padrao evita qualquer superficie de
  redirecionamento aberto por construcao, nao por checagem de host.
  Viaja em 3 saltos ate o redirect final: querystring do GET inicial ->
  campo hidden do formulario de e-mail -> dentro do link do e-mail
  (request_login_token) -> querystring do GET com ?token=.

PublicWorkoutSubscribeView e PublicWorkoutBillingPortalView (Onda B2,
Fatia B/item 6) moram neste mesmo arquivo: precisam da mesma sessao
(cookie) que o login estabelece, e sao so POST de API (sem template
proprio ainda — a tela de assinatura e Onda B3/B4).
"""

from __future__ import annotations

import re

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPhysicalRestrictionTag,
    PublicWorkoutTier,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
)
from public_workouts.services import TrainingIntakeValidationError, get_training_profile, save_training_profile
from public_workouts.stripe_checkout import (
    PublicWorkoutStripeNotConfiguredError,
    start_customer_portal_session,
    start_subscription_checkout,
)

from .public_workout_login import (
    PublicWorkoutLoginRateLimitExceeded,
    request_login_token,
    verify_login_token,
)
from .public_workout_session import attach_public_workout_session_cookie, get_public_workout_account_id_from_request


_PUBLIC_WORKOUT_NEXT_RE = re.compile(r'^/renan/[-a-z0-9]+/?$')
# Literal exato (nao regex — sem parametro nenhum aqui), somado ao padrao de
# /renan/<slug> acima: permite que o login redirecione pra anamnese depois
# do primeiro checkout, sem abrir mao da disciplina de whitelist exata que
# o resto do arquivo ja documenta (nunca url_has_allowed_host_and_scheme,
# que aceitaria qualquer path do mesmo host).
_PUBLIC_WORKOUT_NEXT_LITERALS = ('/treinos/anamnese',)


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
    from public_workouts.models import PublicWorkoutSubscription

    plan_slug = (
        PublicWorkoutSubscription.objects.filter(account_id=account_id)
        .exclude(plan_slug__isnull=True)
        .exclude(plan_slug='')
        .values_list('plan_slug', flat=True)
        .first()
    )
    return f'/renan/{plan_slug}' if plan_slug else ''


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


class PublicWorkoutLoginView(View):
    template_name = 'treinos/login.html'

    def get(self, request, *args, **kwargs):
        token = (request.GET.get('token') or '').strip()
        next_url = _safe_public_workout_next(request.GET.get('next'))
        if not token:
            return render(request, self.template_name, {'next_url': next_url})

        account = verify_login_token(token=token)
        if account is None:
            return render(request, self.template_name, {'error': 'link_invalido', 'next_url': next_url})

        effective_next = next_url or _resolve_default_next_for_account(account.id)
        if effective_next:
            response = redirect(effective_next)
        else:
            response = render(request, self.template_name, {'logged_in_as': account.email})
        attach_public_workout_session_cookie(response, account_id=account.id)
        return response

    def post(self, request, *args, **kwargs):
        email = (request.POST.get('email') or '').strip().lower()
        next_url = _safe_public_workout_next(request.POST.get('next'))
        if not email or '@' not in email:
            return render(request, self.template_name, {'error': 'email_invalido', 'next_url': next_url})

        try:
            request_login_token(email=email, base_url=request.build_absolute_uri('/'), next_url=next_url)
        except PublicWorkoutLoginRateLimitExceeded:
            return render(request, self.template_name, {'error': 'muitos_pedidos', 'next_url': next_url})

        return render(request, self.template_name, {'sent_to': email})


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

        account, _ = PublicWorkoutAccount.objects.get_or_create(email=email)
        subscription = get_or_create_subscription(account=account, tier=tier)

        login_url = request.build_absolute_uri(reverse('public-workout-login'))
        try:
            checkout_url = start_subscription_checkout(
                subscription=subscription,
                success_url=f'{login_url}?assinatura=sucesso',
                cancel_url=f'{login_url}?assinatura=cancelada',
            )
        except PublicWorkoutStripeNotConfiguredError as exc:
            return JsonResponse({'error': 'stripe_nao_configurado', 'detail': str(exc)}, status=503)

        response = JsonResponse({'checkout_url': checkout_url})
        # Ja loga o visitante (attach_public_workout_session_cookie, B1) —
        # sem isso ele precisaria de um segundo round-trip de e-mail/token
        # so pra ver a propria fila de status depois do pagamento.
        return attach_public_workout_session_cookie(response, account_id=account.pk)


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

        return_url = request.build_absolute_uri(reverse('public-workout-login'))
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

        context = self._form_context(account_id)
        context['saved'] = True
        return render(request, self.template_name, context)
