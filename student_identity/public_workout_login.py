"""
ARQUIVO: emissao e verificacao de token de login do corredor de treinos.

POR QUE ELE EXISTE:
- Onda B1 do CORDA (docs/plans/public-workouts-produtizacao-corda.md, S1):
  PublicWorkoutAccount nao tem senha, so token de e-mail. Este modulo
  isola a regra de negocio (rate limit, validade, uso unico) de HTTP — a
  view so chama request_login_token / verify_login_token.

PONTOS CRITICOS:
- Rate limit usa platform_cache (nao o alias 'default'): a conta e
  global, nunca particionada por schema — ver shared_support/platform_cache.py
  e o mesmo raciocinio de shared_support/security/fintech_throttles.py.
- Vinculo com StudentIdentity e resolvido so na CRIACAO da conta (por
  e-mail), nunca ressincronizado depois — informativo, nunca autoritativo
  (N5 do CORDA).
- Falha no envio do e-mail nunca vira 500 pro aluno: o token ja foi
  criado e continua valido, ele so nao recebeu o link ainda.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.utils import timezone

from shared_support.platform_cache import platform_cache

from .delivery_gateways import StudentEmailDeliveryError, get_student_email_gateway
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken

from .models import StudentIdentity

logger = logging.getLogger(__name__)

PUBLIC_WORKOUT_LOGIN_TOKEN_TTL_SECONDS = 900  # 15 min (B1 do CORDA)
PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX = 3
PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 900


class PublicWorkoutLoginRateLimitExceeded(Exception):
    pass


def _rate_limit_key(email: str) -> str:
    return f'octo_pwl_rl_{email}'


def _resolve_student_identity_id(*, email: str) -> int | None:
    return StudentIdentity.objects.filter(email__iexact=email).values_list('id', flat=True).first()


def request_login_token(*, email: str, base_url: str) -> PublicWorkoutLoginToken:
    """Cria (ou reusa) a conta pelo e-mail, emite token e envia o link de login.

    Levanta PublicWorkoutLoginRateLimitExceeded se o e-mail pediu tokens
    demais na janela. Nunca revela se a conta ja existia: a mesma resposta
    (um token novo) sai nos dois casos.
    """
    normalized_email = email.strip().lower()
    rate_limit_key = _rate_limit_key(normalized_email)
    attempts = platform_cache.get(rate_limit_key, 0)
    if attempts >= PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX:
        raise PublicWorkoutLoginRateLimitExceeded(normalized_email)
    platform_cache.set(rate_limit_key, attempts + 1, timeout=PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_WINDOW_SECONDS)

    account, _ = PublicWorkoutAccount.objects.get_or_create(
        email=normalized_email,
        defaults={'student_identity_id': _resolve_student_identity_id(email=normalized_email)},
    )
    token = PublicWorkoutLoginToken.objects.create(
        account=account,
        expires_at=timezone.now() + timezone.timedelta(seconds=PUBLIC_WORKOUT_LOGIN_TOKEN_TTL_SECONDS),
    )

    login_url = f'{base_url.rstrip("/")}/treinos/login?token={token.token}'
    try:
        get_student_email_gateway().send(
            subject='Seu link de acesso — Treinos',
            body=f'Toque para entrar no seu treino (valido por 15 minutos):\n\n{login_url}',
            to_email=normalized_email,
        )
    except StudentEmailDeliveryError:
        logger.exception('public_workout_login_email_failed email=%s', normalized_email)

    return token


def verify_login_token(*, token: str) -> PublicWorkoutAccount | None:
    """Consome o token se valido. None se ausente, mal formado, expirado ou ja usado."""
    try:
        login_token = PublicWorkoutLoginToken.objects.select_related('account').get(token=token)
    except (PublicWorkoutLoginToken.DoesNotExist, ValueError, TypeError, ValidationError):
        return None

    if not login_token.is_valid:
        return None

    login_token.mark_used()
    login_token.save(update_fields=['used_at', 'updated_at'])

    account = login_token.account
    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])

    return account
