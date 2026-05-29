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

    # Stripe substitui o placeholder {CHECKOUT_SESSION_ID} pelo id real da Session.
    # Isso permite que CheckoutSuccessView consulte o status diretamente da API
    # quando o webhook ainda nao chegou (race condition de poucos segundos).
    success_url = (
        _build_absolute_url(
            request,
            reverse('signup-checkout-success') + '?' + urlencode({'pending': pending_signup.pk}),
        )
        + '&session_id={CHECKOUT_SESSION_ID}'
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
# Status publico: consulta Stripe direto para evitar race com webhook
# ─────────────────────────────────────────────────────────────────────────────


def query_stripe_session_status(session_id: str):
    """Retorna informacoes de pagamento da Stripe Session, ou None se nao puder.

    Usado pelo CheckoutSuccessView para confirmar o pagamento antes do webhook
    chegar. Idempotente: nao faz side effect na Stripe, so leitura.

    Retorna dict com:
      - paid: bool — payment_status == 'paid'
      - payment_status: str — valor cru da Stripe
      - amount_total: int — em centavos
      - customer_email: str
      - subscription_id: str
      - customer_id: str
    Ou None se Stripe nao configurado ou erro de rede.
    """
    secret_key = (getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    session_id = (session_id or '').strip()
    if not secret_key or not session_id:
        return None

    try:
        import stripe
    except ImportError:
        logger.warning('query_stripe_session_status: lib stripe nao instalada')
        return None

    stripe.api_key = secret_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.warning('query_stripe_session_status: falha ao consultar session=%s: %s', session_id, exc)
        return None

    return {
        'paid': session.get('payment_status') == 'paid',
        'payment_status': session.get('payment_status', ''),
        'amount_total': session.get('amount_total') or 0,
        'customer_email': session.get('customer_email') or session.get('customer_details', {}).get('email', ''),
        'subscription_id': session.get('subscription') or '',
        'customer_id': session.get('customer') or '',
    }


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
    """Envia email de ativacao com HTML + texto fallback.

    Usa signup.email_sender (provider-aware: SMTP ou Resend), reaproveitando
    settings ja existentes do gateway compartilhado (STUDENT_EMAIL_PROVIDER,
    STUDENT_EMAIL_FROM, STUDENT_RESEND_API_KEY).

    Retorna True se enviou. False se gateway falhou (ja loga o motivo).
    """
    from student_identity.delivery_gateways import StudentEmailDeliveryError
    from .email_sender import send_html_email
    from .notifications import (
        build_owner_onboarding_body,
        build_owner_onboarding_html_body,
        build_owner_onboarding_subject,
    )

    plan_label = pending_signup.get_plan_display()
    subject = build_owner_onboarding_subject(pending_signup.box_name)
    text_body = build_owner_onboarding_body(
        full_name=pending_signup.full_name,
        box_name=pending_signup.box_name,
        plan_label=plan_label,
        activation_url=activation_url,
        expires_in_days=_MAGIC_TOKEN_MAX_AGE_DAYS,
    )
    html_body = build_owner_onboarding_html_body(
        full_name=pending_signup.full_name,
        box_name=pending_signup.box_name,
        plan_label=plan_label,
        activation_url=activation_url,
        expires_in_days=_MAGIC_TOKEN_MAX_AGE_DAYS,
    )
    try:
        send_html_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to_email=pending_signup.email,
        )
    except StudentEmailDeliveryError as exc:
        logger.warning('send_onboarding_email: envio falhou: %s', exc)
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

    APENAS cria o User e marca o signup como ativado. NAO provisiona o Box.
    Para o fluxo completo (User + Box), use activate_and_provision().

    @transaction.atomic: CREATE USER e UPDATE PendingSignup sao transacionais.
    provision_box (DDL: CREATE SCHEMA) NAO pode ser incluido aqui — DDL nao e
    transacional no Postgres. Use transaction.on_commit ou activate_and_provision().
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


def activate_and_provision(*, pending_signup, username: str, raw_password: str):
    """Orquestra ativacao do signup + provisionamento do Box.

    1. activate_pending_signup (atomic): cria User, marca PendingSignup.
    2. provision_box (DDL, fora de transacao): CREATE SCHEMA + migrate + bootstrap.

    Idempotente: se Box ja existe para este pending_signup, retoma steps pendentes.
    Failure mode: se provision_box falhar, User existe mas Box nao. O Owner pode
    tentar de novo via manage.py reprovision_box ou pelo painel de administracao.
    O BoxProvisioningEvent registra o step onde parou.

    Retorna (user, box).
    """
    from control.services import provision_box

    user = activate_pending_signup(
        pending_signup=pending_signup,
        username=username,
        raw_password=raw_password,
    )
    # provision_box fora de @transaction.atomic (DDL nao e transacional no Postgres)
    box = provision_box(
        owner_user=user,
        display_name=pending_signup.box_name or pending_signup.full_name,
        plan=getattr(pending_signup, 'plan', 'monthly') or 'monthly',
        pending_signup=pending_signup,
        stripe_customer_id=getattr(pending_signup, 'stripe_customer_id', '') or '',
        stripe_subscription_id=getattr(pending_signup, 'stripe_subscription_id', '') or '',
    )
    logger.info('activate_and_provision: User=%s Box=%s (schema=%s)', user.username, box.slug, box.schema_name)
    return user, box
