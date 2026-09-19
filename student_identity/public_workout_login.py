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
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.utils import timezone

from shared_support.platform_cache import platform_cache

from .delivery_gateways import StudentEmailDeliveryError
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken

from .models import StudentIdentity
from .public_workout_notifications import (
    build_login_email_body,
    build_login_email_html_body,
    build_login_email_subject,
)

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


def request_login_token(*, email: str, base_url: str, next_url: str = '') -> PublicWorkoutLoginToken:
    """Cria (ou reusa) a conta pelo e-mail, emite token e envia o link de login.

    Levanta PublicWorkoutLoginRateLimitExceeded se o e-mail pediu tokens
    demais na janela. Nunca revela se a conta ja existia: a mesma resposta
    (um token novo) sai nos dois casos.

    `next_url` (opcional, ja validado pelo chamador — ver
    _safe_public_workout_next em public_workout_views.py) viaja dentro do
    proprio link do e-mail. Precisa disso porque o e-mail pode ser aberto
    num dispositivo diferente de onde o login foi pedido — nada de sessao/
    cookie sobrevive esse salto, so o que estiver escrito na URL.
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
    if next_url:
        login_url += f'&next={quote(next_url, safe="")}'

    # Import tardio (nao no topo do arquivo): signup.email_sender importa
    # de student_identity.delivery_gateways — um import no topo daqui
    # criaria ciclo entre os dois apps (mesmo motivo ja documentado em
    # signup/services.py::send_onboarding_email, que faz o mesmo import
    # tardio pro mesmo modulo).
    from signup.email_sender import send_html_email

    expires_in_minutes = PUBLIC_WORKOUT_LOGIN_TOKEN_TTL_SECONDS // 60
    try:
        send_html_email(
            subject=build_login_email_subject(),
            text_body=build_login_email_body(login_url=login_url, expires_in_minutes=expires_in_minutes),
            html_body=build_login_email_html_body(login_url=login_url, expires_in_minutes=expires_in_minutes),
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
