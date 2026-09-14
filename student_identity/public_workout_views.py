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
from django.views.generic import View

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import PublicWorkoutAccount
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


def _safe_public_workout_next(raw: str | None) -> str:
    """So aceita path exato de /renan/<slug> — string vazia pra qualquer
    outra coisa (ausente, absoluto com host, esquema `javascript:`, rota
    fora do corredor). Ver PONTOS CRITICOS no topo do arquivo."""
    candidate = (raw or '').strip()
    return candidate if _PUBLIC_WORKOUT_NEXT_RE.match(candidate) else ''


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

        if next_url:
            response = redirect(next_url)
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

        subscription = get_or_create_subscription(account=account, plan_slug=plan_slug)

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
