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
"""

from __future__ import annotations

from django.shortcuts import render
from django.views.generic import View

from .public_workout_login import (
    PublicWorkoutLoginRateLimitExceeded,
    request_login_token,
    verify_login_token,
)
from .public_workout_session import attach_public_workout_session_cookie


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
