"""
ARQUIVO: recuperação de senha do funcionário por e-mail.

POR QUE ELE EXISTE:
- Funcionário que esquece a senha hoje depende do gestor abrir o admin do Django.
- Concentra as 4 telas do fluxo fora de `access/views.py`, que já cuida de login e papéis.

O QUE ESTE ARQUIVO FAZ:
1. Pede o e-mail e dispara o link assinado (StaffPasswordResetView).
2. Confirma o envio sem revelar se o e-mail existe (StaffPasswordResetSentView).
3. Valida o link e coleta a nova senha (StaffPasswordResetConfirmView).
4. Fecha o ciclo mandando de volta pro login (StaffPasswordResetCompleteView).

PONTOS CRITICOS:
- As rotas VIVEM sob /login/senha/ de propósito. `/login/` está em
  PUBLIC_SCHEMA_PATHS (control/middleware.py) com match por prefixo, então o
  TenantBySessionMiddleware força set_schema_to_public() antes da view rodar.
  `auth_user` só existe no schema public (django.contrib.auth está em
  SHARED_APPS) — em qualquer outro prefixo a query falharia para anônimo.
  Trocar o prefixo aqui SEM mexer no middleware quebra o fluxo inteiro.
- O mesmo prefixo faz o rate limit de scope 'login' (8 POST / 5 min por ator,
  shared_support/security) cobrir o pedido de reset sem configuração extra.
- O token é o `default_token_generator` do Django: HMAC de
  (pk + hash da senha + last_login + timestamp). Consequência: é single-use por
  construção — trocar a senha muda o hash e mata o token — e expira via
  PASSWORD_RESET_TIMEOUT. Não existe (nem precisa) tabela de tokens.
- O envio vai pelo gateway de `signup/email_sender.py` (Resend ou SMTP), não
  pelo EmailMultiAlternatives puro do Django: em produção não há EMAIL_HOST
  configurado, então o caminho SMTP nativo cairia em localhost:25.
- Falha de envio é logada e engolida (mesmo contrato do Django): revelar o erro
  na tela entregaria enumeração de e-mails válidos.
- AppHostRequiredMixin não é cosmético aqui. Sem SESSION_COOKIE_DOMAIN definido,
  o cookie de sessão é host-only; se o confirm rodasse no host de marketing e só
  depois redirecionasse pro app, o token que ele guarda na sessão sumiria no
  caminho. O mixin redireciona no dispatch, ANTES de qualquer escrita de sessão.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.template import loader
from django.urls import reverse_lazy

from signup.email_sender import send_html_email

from .views import AppHostRequiredMixin


logger = logging.getLogger(__name__)


def _reset_timeout_minutes() -> int:
    """Janela de validade do link, em minutos, para a cópia das telas e do e-mail."""
    return max(1, int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 1800)) // 60)


class StaffPasswordResetForm(PasswordResetForm):
    """Form de pedido de reset que despacha pelo gateway de e-mail do projeto.

    `get_users()` do Django já filtra is_active=True e has_usable_password() —
    não sobrescrevemos. Funcionário com e-mail em branco nunca casa, porque o
    campo é EmailField e '' não passa na validação de entrada.

    Quando duas contas dividem o mesmo e-mail (auth.User.email NÃO é unique
    neste projeto — a mesma pessoa pode ser staff de dois boxes), o Django manda
    uma mensagem por conta. Por isso o template do e-mail imprime o username.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'E-mail'
        self.fields['email'].widget.attrs.update({
            'placeholder': 'email@empresa.com',
            'autocomplete': 'email',
            'spellcheck': 'false',
            'aria-describedby': 'reset-email-note',
        })

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = ''.join(loader.render_to_string(subject_template_name, context).splitlines()).strip()
        text_body = loader.render_to_string(email_template_name, context)
        html_body = loader.render_to_string(html_email_template_name or email_template_name, context)

        try:
            send_html_email(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                to_email=to_email,
            )
        except Exception:
            # Mesmo contrato do PasswordResetForm nativo: loga e segue. A tela
            # de sucesso é idêntica com ou sem falha, senão vira oráculo de
            # e-mails válidos. Sentry captura pelo logger.exception.
            logger.exception(
                'staff_password_reset_email_failed user_id=%s',
                getattr(context.get('user'), 'pk', None),
            )


class StaffSetPasswordForm(SetPasswordForm):
    """Coleta a nova senha aplicando os validators de AUTH_PASSWORD_VALIDATORS."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Nova senha'
        self.fields['new_password2'].label = 'Confirme a nova senha'
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Sua nova senha',
            'autocomplete': 'new-password',
            'aria-describedby': 'reset-password-note',
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Repita a nova senha',
            'autocomplete': 'new-password',
        })


class StaffPasswordResetView(AppHostRequiredMixin, PasswordResetView):
    """Tela 1 — pede o e-mail e dispara o link."""

    template_name = 'access/password_reset_request.html'
    subject_template_name = 'access/emails/password_reset_subject.txt'
    email_template_name = 'access/emails/password_reset_email.txt'
    html_email_template_name = 'access/emails/password_reset_email.html'
    form_class = StaffPasswordResetForm
    success_url = reverse_lazy('password-reset-sent')

    @property
    def extra_email_context(self):
        # Property (e não atributo de classe) para que override_settings de
        # PASSWORD_RESET_TIMEOUT valha nos testes.
        return {'timeout_minutes': _reset_timeout_minutes()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_minutes'] = _reset_timeout_minutes()
        return context


class StaffPasswordResetSentView(AppHostRequiredMixin, PasswordResetDoneView):
    """Tela 2 — confirma o envio sem confirmar que a conta existe."""

    template_name = 'access/password_reset_sent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_minutes'] = _reset_timeout_minutes()
        return context


class StaffPasswordResetConfirmView(AppHostRequiredMixin, PasswordResetConfirmView):
    """Tela 3 — valida o link e troca a senha.

    post_reset_login fica False (padrão do Django) de propósito: quem chega aqui
    provou acesso ao e-mail, não à conta. O funcionário passa pelo login normal
    com a senha nova, e aí o throttle de 'login' volta a valer.
    """

    template_name = 'access/password_reset_confirm.html'
    form_class = StaffSetPasswordForm
    success_url = reverse_lazy('password-reset-complete')


class StaffPasswordResetCompleteView(AppHostRequiredMixin, PasswordResetCompleteView):
    """Tela 4 — fecha o ciclo e devolve pro login interno."""

    template_name = 'access/password_reset_complete.html'


__all__ = [
    'StaffPasswordResetForm',
    'StaffSetPasswordForm',
    'StaffPasswordResetView',
    'StaffPasswordResetSentView',
    'StaffPasswordResetConfirmView',
    'StaffPasswordResetCompleteView',
]
