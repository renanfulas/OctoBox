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

import hashlib
import hmac
import logging
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

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


# Código digitado no próprio app: o link do e-mail abre fora do app instalado
# (no iPhone, Safari e o app da tela inicial não compartilham cookies), então
# quem já está logado confirma a identidade sem sair dele.
PUBLIC_WORKOUT_LOGIN_CODE_ATTEMPTS_MAX = 5
PUBLIC_WORKOUT_LOGIN_CODE_WINDOW_SECONDS = 900
PUBLIC_WORKOUT_LOGIN_CODE_CANDIDATES = 5


class PublicWorkoutLoginRateLimitExceeded(Exception):
    pass


class PublicWorkoutLoginCodeAttemptsExceeded(Exception):
    pass


def _rate_limit_key(email: str) -> str:
    return f'octo_pwl_rl_{email}'


def _code_attempts_key(account_id: int) -> str:
    return f'octo_pwl_code_{account_id}'


def login_code_for_token(token) -> str:
    """Código de 6 dígitos derivado do token por HMAC com a SECRET_KEY.

    O mesmo e-mail carrega o link e o código; derivar do token evita coluna
    nova e herda validade, uso único e expiração do próprio token."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(), f'curva-login-code:{token}'.encode(), hashlib.sha256,
    ).hexdigest()
    return str(int(digest[:12], 16) % 1_000_000).zfill(6)


def _resolve_student_identity_id(*, email: str) -> int | None:
    return StudentIdentity.objects.filter(email__iexact=email).values_list('id', flat=True).first()


def resolve_or_create_public_workout_account(*, email: str, photo_url: str = '') -> PublicWorkoutAccount:
    """Acha ou cria a PublicWorkoutAccount pelo e-mail — usado tanto pelo
    login por e-mail (abaixo) quanto pelo login por Google
    (public_workout_oauth.py). Um so lugar decide como resolver conta a
    partir de um e-mail vindo de fora; o vinculo com StudentIdentity
    continua so informativo (N5 do CORDA).

    `photo_url` (opcional, so' o login por Google tem uma pra oferecer —
    ver identity.photo_url em oauth_providers.py) so' ATUALIZA a conta
    quando vem preenchido; login por e-mail (chama sem esse argumento)
    nunca limpa uma foto que ja existia. Conta nova via Google ja nasce
    com a foto; conta que so' tinha e-mail ganha a foto na primeira vez
    que logar por Google."""
    normalized_email = email.strip().lower()
    photo_url = (photo_url or '').strip()
    account, created = PublicWorkoutAccount.objects.get_or_create(
        email=normalized_email,
        defaults={
            'student_identity_id': _resolve_student_identity_id(email=normalized_email),
            'photo_url': photo_url,
        },
    )
    if not created and photo_url and account.photo_url != photo_url:
        account.photo_url = photo_url
        account.save(update_fields=['photo_url', 'updated_at'])
    return account


def request_login_token(*, email: str, base_url: str, next_url: str = '') -> PublicWorkoutLoginToken | None:
    """Emite e envia link de login apenas para uma conta existente e elegível.

    Levanta PublicWorkoutLoginRateLimitExceeded se o e-mail pediu tokens
    demais na janela. Returns None when no eligible account exists; signup
    and payment are handled by the checkout flow instead.

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

    account = PublicWorkoutAccount.objects.filter(email__iexact=normalized_email).first()
    if account is None:
        return None
    subscription = getattr(account, 'subscription', None)
    if subscription is not None and subscription.requires_login and subscription.status == 'pending_payment':
        return None
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
    code = login_code_for_token(token.token)
    try:
        send_html_email(
            subject=build_login_email_subject(),
            text_body=build_login_email_body(login_url=login_url, expires_in_minutes=expires_in_minutes, code=code),
            html_body=build_login_email_html_body(login_url=login_url, expires_in_minutes=expires_in_minutes, code=code),
            to_email=normalized_email,
        )
    except StudentEmailDeliveryError:
        logger.exception('public_workout_login_email_failed email=%s', normalized_email)

    return token


def verify_login_token(*, token: str) -> PublicWorkoutAccount | None:
    """Consome o token se valido. None se ausente, mal formado, expirado ou ja usado.

    A linha do token fica travada entre a leitura e o mark_used(): dois cliques
    simultaneos no mesmo link nao abrem duas sessoes — o segundo espera o
    primeiro commitar e ja le o token como usado.
    """
    with transaction.atomic():
        try:
            login_token = (
                PublicWorkoutLoginToken.objects
                .select_for_update(of=('self',))
                .select_related('account')
                .get(token=token)
            )
        except (PublicWorkoutLoginToken.DoesNotExist, ValueError, TypeError, ValidationError):
            return None

        if not login_token.is_valid:
            return None

        account = login_token.account
        subscription = getattr(account, 'subscription', None)
        if subscription is not None and subscription.requires_login and subscription.status == 'pending_payment':
            return None
        login_token.mark_used()
        login_token.save(update_fields=['used_at', 'updated_at'])

    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])

    return account


def verify_login_code(*, account_id: int, code) -> PublicWorkoutAccount | None:
    """Consome o token cujo código bate, só entre os tokens da conta já logada.

    Quem chama já resolveu `account_id` pelo cookie do aparelho: o código não
    procura conta, só prova que esta conta lê o próprio e-mail. Tentativas são
    limitadas por conta; o token casado é travado na linha para duas
    confirmações simultâneas não passarem as duas. None se não bater, se o
    token expirou/foi usado ou se a assinatura ainda aguarda pagamento.
    """
    attempts_key = _code_attempts_key(account_id)
    attempts = platform_cache.get(attempts_key, 0)
    if attempts >= PUBLIC_WORKOUT_LOGIN_CODE_ATTEMPTS_MAX:
        raise PublicWorkoutLoginCodeAttemptsExceeded(account_id)
    platform_cache.set(attempts_key, attempts + 1, timeout=PUBLIC_WORKOUT_LOGIN_CODE_WINDOW_SECONDS)

    normalized = ''.join(char for char in str(code or '') if char.isdigit())
    if len(normalized) != 6:
        return None
    with transaction.atomic():
        candidates = list(
            PublicWorkoutLoginToken.objects
            .select_for_update(of=('self',))
            .select_related('account')
            .filter(account_id=account_id, used_at__isnull=True, expires_at__gt=timezone.now())
            .order_by('-created_at')[:PUBLIC_WORKOUT_LOGIN_CODE_CANDIDATES]
        )
        login_token = next(
            (item for item in candidates if constant_time_compare(login_code_for_token(item.token), normalized)),
            None,
        )
        if login_token is None:
            return None
        account = login_token.account
        subscription = getattr(account, 'subscription', None)
        if subscription is not None and subscription.requires_login and subscription.status == 'pending_payment':
            return None
        login_token.mark_used()
        login_token.save(update_fields=['used_at', 'updated_at'])

    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])
    platform_cache.delete(attempts_key)
    return account
