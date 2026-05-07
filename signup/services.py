"""
ARQUIVO: orquestracao do ciclo Early Adopter ponta a ponta.

POR QUE ELE EXISTE:
- Isola a chamada a Stripe da view, mantendo a view enxuta.
- Permite plugar o Price ID correto baseado no plano escolhido.
- Tolera ambiente sem Stripe configurado (dev local) sem quebrar o fluxo de teste visual.
- Concentra magic-token, email de ativacao e provisao de Owner pos-pagamento.

O QUE ESTE ARQUIVO FAZ:
1. Le STRIPE_PRICE_EARLY_MONTHLY e STRIPE_PRICE_EARLY_ANNUAL das settings.
2. Cria stripe.checkout.Session em modo subscription, com metadata do PendingSignup.
3. Retorna a URL hospedada da Stripe para redirect.
4. Marca o PendingSignup como pago quando o webhook chega.
5. Gera magic-token assinado e dispara email de ativacao.
6. Provisiona User com role Owner e marca PendingSignup como ativado.

PONTOS CRITICOS:
- A chave secreta da Stripe e configurada em integrations/stripe/auth.py — reusamos.
- A idempotencia e construida com o id do PendingSignup para evitar Sessions duplicadas.
- Quando os Price IDs nao estao setados (ambiente dev sem Stripe), levanta StripeNotConfiguredError
  para que a view exiba um aviso amigavel em vez de redirecionar para Stripe quebrada.
- O magic-token usa django.core.signing com SECRET_KEY rotativa — sem persistencia de hash.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone


logger = logging.getLogger(__name__)


_MAGIC_TOKEN_SALT = 'signup.onboarding.magic-token.v1'
_MAGIC_TOKEN_MAX_AGE_DAYS = 7


class StripeNotConfiguredError(RuntimeError):
    """Levantado quando STRIPE_PRICE_EARLY_* nao estao definidos."""


class InvalidMagicTokenError(RuntimeError):
    """Levantado quando o magic-token e invalido, expirado ou ja consumido."""


def _resolve_price_id(plan: str) -> str:
    if plan == 'monthly':
        price_id = getattr(settings, 'STRIPE_PRICE_EARLY_MONTHLY', '') or ''
    elif plan == 'annual':
        price_id = getattr(settings, 'STRIPE_PRICE_EARLY_ANNUAL', '') or ''
    else:
        raise ValueError(f'Plano desconhecido: {plan!r}')

    if not price_id:
        raise StripeNotConfiguredError(
            'STRIPE_PRICE_EARLY_MONTHLY e STRIPE_PRICE_EARLY_ANNUAL ainda nao foram '
            'configurados. Defina-os no .env e reinicie o servidor.'
        )
    return price_id


def _build_absolute_url(request, path):
    return request.build_absolute_uri(path)


def create_checkout_session(pending_signup, request):
    """Cria uma stripe.checkout.Session em modo subscription para o PendingSignup.

    Retorna a URL hospedada que o cliente deve abrir para pagar.
    """
    price_id = _resolve_price_id(pending_signup.plan)

    # Import tardio para nao tornar o app dependente da lib stripe em ambientes
    # de teste que nao precisam dela (e para nao explodir caso a lib falte localmente).
    import stripe

    secret_key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not secret_key:
        raise StripeNotConfiguredError('STRIPE_SECRET_KEY nao definida.')
    stripe.api_key = secret_key

    success_url = _build_absolute_url(
        request,
        reverse('signup-checkout-success') + '?' + urlencode({'pending': pending_signup.pk}),
    )
    cancel_url = _build_absolute_url(
        request,
        reverse('signup-checkout-canceled') + '?' + urlencode({'pending': pending_signup.pk}),
    )

    session = stripe.checkout.Session.create(
        mode='subscription',
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        customer_email=pending_signup.email,
        client_reference_id=str(pending_signup.pk),
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=False,
        metadata={
            'pending_signup_id': str(pending_signup.pk),
            'plan': pending_signup.plan,
            'box_name': pending_signup.box_name,
        },
        subscription_data={
            'metadata': {
                'pending_signup_id': str(pending_signup.pk),
                'plan': pending_signup.plan,
            },
        },
        idempotency_key=f'pending-signup-{pending_signup.pk}-{pending_signup.plan}',
    )

    pending_signup.stripe_session_id = session.id
    pending_signup.save(update_fields=['stripe_session_id', 'updated_at'])

    return session.url


# ─────────────────────────────────────────────────────────────────────────────
# Pos-pagamento: marca como pago, gera magic token e envia email
# ─────────────────────────────────────────────────────────────────────────────


def mark_pending_signup_paid(*, pending_signup_id, stripe_session_id='', stripe_customer_id='', stripe_subscription_id=''):
    """Marca o PendingSignup como pago. Idempotente.

    Chamado pelo webhook handler do Stripe quando `checkout.session.completed`
    chega referenciando um pending_signup_id na metadata.
    """
    from .models import PendingSignup, PendingSignupStatus

    pending = PendingSignup.objects.filter(pk=pending_signup_id).first()
    if pending is None:
        logger.warning('mark_pending_signup_paid: pending_signup_id=%s nao encontrado', pending_signup_id)
        return None

    if pending.status == PendingSignupStatus.ACTIVATED:
        logger.info('mark_pending_signup_paid: ja ativado, ignorando. pending=%s', pending.pk)
        return pending

    fields_to_update = ['updated_at']
    if pending.status != PendingSignupStatus.PAID:
        pending.status = PendingSignupStatus.PAID
        fields_to_update.append('status')

    if stripe_session_id and pending.stripe_session_id != stripe_session_id:
        pending.stripe_session_id = stripe_session_id
        fields_to_update.append('stripe_session_id')

    if stripe_customer_id:
        pending.stripe_customer_id = stripe_customer_id
        fields_to_update.append('stripe_customer_id')

    if stripe_subscription_id:
        pending.stripe_subscription_id = stripe_subscription_id
        fields_to_update.append('stripe_subscription_id')

    if not pending.magic_token_expires_at or pending.magic_token_expires_at < timezone.now():
        pending.magic_token_expires_at = timezone.now() + timedelta(days=_MAGIC_TOKEN_MAX_AGE_DAYS)
        fields_to_update.append('magic_token_expires_at')

    pending.save(update_fields=fields_to_update)
    return pending


def generate_magic_token(pending_signup) -> str:
    """Token assinado (HMAC + timestamp) que so contem o pk do PendingSignup."""
    return signing.dumps({'pk': pending_signup.pk}, salt=_MAGIC_TOKEN_SALT)


def verify_magic_token(token: str):
    """Resolve o token em PendingSignup ou levanta InvalidMagicTokenError.

    Valida assinatura, expiracao e estado do PendingSignup (so aceita PAID).
    """
    from .models import PendingSignup, PendingSignupStatus

    if not token:
        raise InvalidMagicTokenError('token-vazio')

    try:
        max_age_seconds = _MAGIC_TOKEN_MAX_AGE_DAYS * 24 * 60 * 60
        data = signing.loads(token, salt=_MAGIC_TOKEN_SALT, max_age=max_age_seconds)
    except signing.SignatureExpired:
        raise InvalidMagicTokenError('token-expirado')
    except signing.BadSignature:
        raise InvalidMagicTokenError('token-invalido')

    pending = PendingSignup.objects.filter(pk=data.get('pk')).first()
    if pending is None:
        raise InvalidMagicTokenError('pending-nao-encontrado')

    if pending.status == PendingSignupStatus.ACTIVATED:
        raise InvalidMagicTokenError('ja-ativado')

    if pending.status != PendingSignupStatus.PAID:
        raise InvalidMagicTokenError(f'status-invalido:{pending.status}')

    return pending


def send_onboarding_email(pending_signup, *, activation_url: str) -> bool:
    """Envia email de ativacao usando o gateway compartilhado de student_identity.

    Retorna True se enviou. False se gateway falhou (ja loga o motivo).
    """
    from student_identity.delivery_gateways import (
        StudentEmailDeliveryError,
        get_student_email_gateway,
    )
    from .notifications import build_owner_onboarding_body, build_owner_onboarding_subject

    gateway = get_student_email_gateway()
    plan_label = pending_signup.get_plan_display()
    subject = build_owner_onboarding_subject(pending_signup.box_name)
    body = build_owner_onboarding_body(
        full_name=pending_signup.full_name,
        box_name=pending_signup.box_name,
        plan_label=plan_label,
        activation_url=activation_url,
        expires_in_days=_MAGIC_TOKEN_MAX_AGE_DAYS,
    )
    try:
        gateway.send(subject=subject, body=body, to_email=pending_signup.email)
    except StudentEmailDeliveryError as exc:
        logger.warning('send_onboarding_email: gateway %s falhou: %s', gateway.provider_name, exc)
        return False
    except Exception:
        logger.exception('send_onboarding_email: erro inesperado ao enviar email')
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Ativacao: cria User Owner e marca PendingSignup como activated
# ─────────────────────────────────────────────────────────────────────────────


class UsernameTakenError(RuntimeError):
    """Username escolhido ja existe."""


@transaction.atomic
def activate_pending_signup(*, pending_signup, username: str, raw_password: str):
    """Cria User com role Owner, vincula ao PendingSignup e finaliza o ciclo.

    Reusa a logica do comando access.management.commands.provision_owner:
    cria User ativo, atribui Group 'Owner', preenche first_name/last_name.
    """
    from .models import PendingSignupStatus

    user_model = get_user_model()
    username = (username or '').strip()
    if not username:
        raise ValueError('username-obrigatorio')

    if user_model.objects.filter(username=username).exists():
        raise UsernameTakenError(username)

    try:
        owner_group = Group.objects.get(name='Owner')
    except Group.DoesNotExist:
        owner_group = None
        logger.error('activate_pending_signup: grupo Owner nao existe — rode bootstrap_roles')

    parts = pending_signup.full_name.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    user = user_model.objects.create_user(
        username=username,
        email=pending_signup.email,
        password=raw_password,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )
    if owner_group is not None:
        user.groups.add(owner_group)

    pending_signup.status = PendingSignupStatus.ACTIVATED
    pending_signup.activated_at = timezone.now()
    pending_signup.activated_user = user
    pending_signup.save(update_fields=['status', 'activated_at', 'activated_user', 'updated_at'])

    return user
