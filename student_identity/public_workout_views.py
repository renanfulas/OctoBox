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
- B1 nao inclui roteamento pro treino certo da conta (isso e Onda B3,
  ownership do slug) — so a sessao fica pronta aqui.

PublicWorkoutSubscribeView (Onda B2, Fatia B) mora neste mesmo arquivo:
precisa da mesma sessao (cookie) que o login estabelece, e e so um POST
de API (sem template proprio ainda — a tela de assinatura e Onda B3/B4).
"""

from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import PublicWorkoutAccount
from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError, start_subscription_checkout

from .public_workout_login import (
    PublicWorkoutLoginRateLimitExceeded,
    request_login_token,
    verify_login_token,
)
from .public_workout_session import attach_public_workout_session_cookie, get_public_workout_account_id_from_request


class PublicWorkoutLoginView(View):
    template_name = 'treinos/login.html'

    def get(self, request, *args, **kwargs):
        token = (request.GET.get('token') or '').strip()
        if not token:
            return render(request, self.template_name, {})

        account = verify_login_token(token=token)
        if account is None:
            return render(request, self.template_name, {'error': 'link_invalido'})

        response = render(request, self.template_name, {'logged_in_as': account.email})
        attach_public_workout_session_cookie(response, account_id=account.id)
        return response

    def post(self, request, *args, **kwargs):
        email = (request.POST.get('email') or '').strip().lower()
        if not email or '@' not in email:
            return render(request, self.template_name, {'error': 'email_invalido'})

        try:
            request_login_token(email=email, base_url=request.build_absolute_uri('/'))
        except PublicWorkoutLoginRateLimitExceeded:
            return render(request, self.template_name, {'error': 'muitos_pedidos'})

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
