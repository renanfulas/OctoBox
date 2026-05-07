"""
ARQUIVO: views publicas do fluxo Early Adopter.

POR QUE ELE EXISTE:
- Recebe o trafego vindo da landing octoboxfit.com.br/_preview/landing/.
- Cria o PendingSignup, dispara a Stripe Checkout Session e mostra o estado pos-pagamento.

O QUE ESTE ARQUIVO FAZ:
1. CheckoutFormView: GET renderiza form, POST cria PendingSignup e redireciona para Stripe.
2. CheckoutSuccessView: pagina de espera pos-pagamento ("verifique seu email").
3. CheckoutCanceledView: usuario abandonou — registra status e oferece retomar.

PONTOS CRITICOS:
- Em DEV, se STRIPE_PRICE_EARLY_* nao estao definidos, a view degrada graciosamente
  para uma pagina informativa em vez de quebrar.
- O parametro `plan` na querystring vem da landing; valores fora do whitelist
  caem para `annual` por seguranca.
"""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from .forms import CheckoutForm, OnboardingForm
from .models import PendingSignup, PendingSignupPlan, PendingSignupStatus
from .services import (
    InvalidMagicTokenError,
    StripeNotConfiguredError,
    UsernameTakenError,
    activate_pending_signup,
    create_checkout_session,
    verify_magic_token,
)


logger = logging.getLogger(__name__)


_VALID_PLANS = {p.value for p in PendingSignupPlan}


def _resolve_plan(raw_value):
    candidate = (raw_value or '').strip().lower()
    if candidate in _VALID_PLANS:
        return candidate
    return PendingSignupPlan.ANNUAL.value


def _plan_display(plan_value):
    if plan_value == PendingSignupPlan.MONTHLY.value:
        return {'label': 'Mensal', 'amount': 'R$ 97', 'period': 'por mês', 'savings_label': ''}
    return {'label': 'Anual', 'amount': 'R$ 997', 'period': 'por ano', 'savings_label': 'Economize R$ 167 vs mensal'}


class CheckoutFormView(FormView):
    template_name = 'signup/checkout.html'
    form_class = CheckoutForm

    def get_initial(self):
        initial = super().get_initial()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = _resolve_plan(self.request.GET.get('plan'))
        context['plan'] = plan
        context['plan_display'] = _plan_display(plan)
        context['post_program_price'] = 'R$ 197/mês'
        return context

    def form_valid(self, form):
        plan = _resolve_plan(self.request.POST.get('plan') or self.request.GET.get('plan'))
        referer = (self.request.META.get('HTTP_REFERER') or '')[:255]

        pending = PendingSignup.objects.create(
            email=form.cleaned_data['email'],
            full_name=form.cleaned_data['full_name'],
            box_name=form.cleaned_data['box_name'],
            phone=form.cleaned_data['phone'],
            plan=plan,
            landing_referer=referer,
        )

        try:
            session_url = create_checkout_session(pending, self.request)
        except StripeNotConfiguredError as exc:
            logger.warning('Stripe nao configurado para Early Adopters: %s', exc)
            messages.warning(
                self.request,
                'Recebemos seu interesse! O pagamento online ainda esta sendo configurado. '
                'Vamos chamar voce no WhatsApp em ate 12h.',
            )
            return HttpResponseRedirect(_pending_path(pending))
        except Exception:
            logger.exception('Falha inesperada ao criar Stripe Checkout Session.')
            messages.error(
                self.request,
                'Algo deu errado ao iniciar o pagamento. Nossa equipe ja foi avisada — '
                'vamos te chamar no WhatsApp em instantes.',
            )
            return HttpResponseRedirect(_pending_path(pending))

        return HttpResponseRedirect(session_url)


class CheckoutSuccessView(TemplateView):
    template_name = 'signup/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_id = self.request.GET.get('pending')
        pending = None
        if pending_id and pending_id.isdigit():
            pending = PendingSignup.objects.filter(pk=int(pending_id)).first()
        context['pending'] = pending
        context['mode'] = 'success'
        return context


class CheckoutCanceledView(TemplateView):
    template_name = 'signup/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_id = self.request.GET.get('pending')
        pending = None
        if pending_id and pending_id.isdigit():
            pending = PendingSignup.objects.filter(pk=int(pending_id)).first()
            if pending and pending.status == PendingSignupStatus.PENDING:
                pending.status = PendingSignupStatus.CANCELED
                pending.save(update_fields=['status', 'updated_at'])
        context['pending'] = pending
        context['mode'] = 'canceled'
        return context


class CheckoutPendingStripeView(TemplateView):
    """Tela amigavel quando Stripe nao esta configurado (dev) ou falhou.

    Permite ao operador (Renan) ver o PendingSignup e contatar via WhatsApp.
    """

    template_name = 'signup/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_id = kwargs.get('pending_id')
        pending = get_object_or_404(PendingSignup, pk=pending_id)
        context['pending'] = pending
        context['mode'] = 'manual_followup'
        return context


def _pending_path(pending):
    return reverse('signup-checkout-pending', kwargs={'pending_id': pending.pk})


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding pos-pagamento (magic link)
# ─────────────────────────────────────────────────────────────────────────────


class OnboardingWizardView(FormView):
    """Wizard de 1 tela: define username + senha e cria a conta Owner.

    Acessada via /onboarding/<token>/. Token e HMAC-signed com expiracao de 7 dias.
    """

    template_name = 'signup/onboarding.html'
    form_class = OnboardingForm

    def dispatch(self, request, *args, **kwargs):
        token = kwargs.get('token', '')
        try:
            self.pending = verify_magic_token(token)
        except InvalidMagicTokenError as exc:
            self.pending = None
            self.token_error = str(exc)
        else:
            self.token_error = None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending'] = self.pending
        context['token_error'] = self.token_error
        context['suggested_username'] = self._suggest_username() if self.pending else ''
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.pending:
            initial['username'] = self._suggest_username()
        return initial

    def _suggest_username(self) -> str:
        """Sugere um username a partir do email do PendingSignup, sem dominio."""
        if not self.pending:
            return ''
        local = self.pending.email.split('@', 1)[0]
        clean = ''.join(ch if ch.isalnum() or ch in '._-' else '' for ch in local).lower()
        return clean[:32]

    def form_valid(self, form):
        if self.pending is None:
            messages.error(self.request, 'Link de ativação inválido ou expirado.')
            return self.render_to_response(self.get_context_data(form=form))

        try:
            user = activate_pending_signup(
                pending_signup=self.pending,
                username=form.cleaned_data['username'],
                raw_password=form.cleaned_data['password'],
            )
        except UsernameTakenError:
            form.add_error('username', 'Este nome de usuário já está em uso. Escolha outro.')
            return self.render_to_response(self.get_context_data(form=form))
        except Exception:
            logger.exception('OnboardingWizardView: falha ao ativar PendingSignup pk=%s', self.pending.pk)
            messages.error(
                self.request,
                'Algo deu errado ao criar sua conta. Nossa equipe vai te chamar no WhatsApp em instantes.',
            )
            return self.render_to_response(self.get_context_data(form=form))

        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        return HttpResponseRedirect(reverse('access-overview'))
