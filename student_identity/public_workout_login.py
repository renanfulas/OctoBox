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
# Na tela de login o código chega com um e-mail digitado, não com o cookie:
# o teto por conta não segura quem testa um código em muitos e-mails, então
# o IP também tem teto. Só falhas contam; uma academia no mesmo Wi-Fi não
# trava quem acerta.
PUBLIC_WORKOUT_LOGIN_CODE_IP_FAILURES_MAX = 20


class PublicWorkoutLoginRateLimitExceeded(Exception):
    pass


class PublicWorkoutLoginCodeAttemptsExceeded(Exception):
    pass


def _rate_limit_key(email: str) -> str:
    return f'octo_pwl_rl_{email}'


def _code_attempts_key(account_id: int) -> str:
    return f'octo_pwl_code_{account_id}'


def _unknown_email_code_attempts_key(email: str) -> str:
    return f'octo_pwl_code_e_{hashlib.sha256(email.encode()).hexdigest()[:24]}'


def _code_ip_failures_key(client_ip: str) -> str:
    return f'octo_pwl_code_ip_{hashlib.sha256(client_ip.encode()).hexdigest()[:24]}'


def _consume_code_attempt(key: str) -> None:
    attempts = platform_cache.get(key, 0)
    if attempts >= PUBLIC_WORKOUT_LOGIN_CODE_ATTEMPTS_MAX:
        raise PublicWorkoutLoginCodeAttemptsExceeded(key)
    platform_cache.set(key, attempts + 1, timeout=PUBLIC_WORKOUT_LOGIN_CODE_WINDOW_SECONDS)


def mask_login_email(email: str) -> str:
    """`fu•••@dominio`: reconhecível por quem é dono, inútil para quem não é."""
    local, _, domain = (email or '').partition('@')
    return f'{local[:2]}•••@{domain}' if domain else '•••'


def _log_login_failure(reason: str, *, channel: str, account_id: int | None = None, **extra) -> None:
    """Motivo de cada login recusado, para medir o que trava o aluno.

    Nunca recebe token nem e-mail: o id da conta basta para cruzar com o banco.
    """
    details = ''.join(f' {key}={value}' for key, value in extra.items())
    logger.warning(
        'public_workout_login_failed reason=%s channel=%s account_id=%s%s',
        reason, channel, account_id if account_id is not None else '-', details,
    )


def _pending_payment(account: PublicWorkoutAccount) -> bool:
    subscription = getattr(account, 'subscription', None)
    return subscription is not None and subscription.requires_login and subscription.status == 'pending_payment'


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
    if account is None or _pending_payment(account):
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


def find_login_token(token) -> PublicWorkoutLoginToken | None:
    """Lê o token sem travar nem consumir — a tela de confirmação só mostra a conta."""
    try:
        return PublicWorkoutLoginToken.objects.select_related('account').filter(token=token).first()
    except (ValueError, TypeError, ValidationError):
        return None


def login_token_refusal(login_token: PublicWorkoutLoginToken | None) -> str | None:
    """Por que este token não entra, ou None se ainda entra. Não loga nem trava."""
    if login_token is None:
        return 'nao_encontrado'
    if login_token.used_at is not None:
        return 'ja_usado'
    if login_token.is_expired:
        return 'expirado'
    if _pending_payment(login_token.account):
        return 'pagamento_pendente'
    return None


def _log_login_token_refusal(reason: str, login_token: PublicWorkoutLoginToken | None) -> None:
    if login_token is None:
        _log_login_failure(reason, channel='link')
        return
    now = timezone.now()
    extra = {}
    if reason == 'ja_usado':
        # Poucos segundos entre o envio e o uso apontam para scanner de e-mail
        # ou prévia de link, não para o aluno.
        extra = {
            'seconds_since_used': int((now - login_token.used_at).total_seconds()),
            'seconds_from_created_to_used': int((login_token.used_at - login_token.created_at).total_seconds()),
        }
    elif reason == 'expirado':
        extra = {'seconds_since_expired': int((now - login_token.expires_at).total_seconds())}
    _log_login_failure(reason, channel='link', account_id=login_token.account_id, **extra)


def check_login_token(login_token: PublicWorkoutLoginToken | None) -> str | None:
    """Motivo da recusa para a tela do GET (já no log), ou None; não consome.

    Recebe o resultado de `find_login_token`. O POST revalida tudo sob trava
    em `verify_login_token`.
    """
    reason = login_token_refusal(login_token)
    if reason:
        _log_login_token_refusal(reason, login_token)
    return reason


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
            login_token = None

        reason = login_token_refusal(login_token)
        if reason:
            _log_login_token_refusal(reason, login_token)
            return None

        account = login_token.account
        login_token.mark_used()
        login_token.save(update_fields=['used_at', 'updated_at'])

    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])

    return account


def verify_login_code(*, account_id: int, code, channel: str = 'app') -> PublicWorkoutAccount | None:
    """Consome o token cujo código bate, só entre os tokens da conta já logada.

    Quem chama já resolveu `account_id` pelo cookie do aparelho: o código não
    procura conta, só prova que esta conta lê o próprio e-mail. Tentativas são
    limitadas por conta; o token casado é travado na linha para duas
    confirmações simultâneas não passarem as duas. None se não bater, se o
    token expirou/foi usado ou se a assinatura ainda aguarda pagamento.
    """
    attempts_key = _code_attempts_key(account_id)
    _consume_code_attempt(attempts_key)

    normalized = ''.join(char for char in str(code or '') if char.isdigit())
    if len(normalized) != 6:
        _log_login_failure('codigo_invalido', channel=channel, account_id=account_id)
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
            _log_login_failure('codigo_invalido', channel=channel, account_id=account_id)
            return None
        account = login_token.account
        if _pending_payment(account):
            _log_login_failure('pagamento_pendente', channel=channel, account_id=account_id)
            return None
        login_token.mark_used()
        login_token.save(update_fields=['used_at', 'updated_at'])

    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])
    platform_cache.delete(attempts_key)
    return account


def verify_login_code_for_email(*, email: str, code, client_ip: str) -> PublicWorkoutAccount | None:
    """Código digitado na tela de login, para quem não tem cookie nenhum.

    Mesma regra de `verify_login_code` (candidatos, trava da linha, pagamento
    pendente, teto por conta); a conta vem do e-mail digitado. Quem chama
    responde igual para e-mail sem conta e código errado: o e-mail sem conta
    também tem teto de tentativas, então seis palpites não dizem se a conta
    existe. Levanta PublicWorkoutLoginCodeAttemptsExceeded no teto da conta
    ou do IP.
    """
    ip_key = _code_ip_failures_key(client_ip or 'unknown')
    if not platform_cache.add(ip_key, 1, timeout=PUBLIC_WORKOUT_LOGIN_CODE_WINDOW_SECONDS):
        try:
            failures = platform_cache.incr(ip_key)
        except ValueError:
            platform_cache.set(ip_key, 1, timeout=PUBLIC_WORKOUT_LOGIN_CODE_WINDOW_SECONDS)
            failures = 1
        if failures > PUBLIC_WORKOUT_LOGIN_CODE_IP_FAILURES_MAX:
            _log_login_failure('muitas_tentativas_ip', channel='login')
            raise PublicWorkoutLoginCodeAttemptsExceeded(ip_key)

    normalized_email = (email or '').strip().lower()
    account_id = (
        PublicWorkoutAccount.objects.filter(email__iexact=normalized_email).values_list('id', flat=True).first()
        if normalized_email else None
    )
    if account_id is None:
        _consume_code_attempt(_unknown_email_code_attempts_key(normalized_email))
        _log_login_failure('nao_encontrado', channel='login')
        return None

    account = verify_login_code(account_id=account_id, code=code, channel='login')
    if account is not None:
        # A tentativa já foi contada antes de saber o resultado; acerto não
        # gasta a cota do IP.
        try:
            platform_cache.decr(ip_key)
        except ValueError:
            pass
    return account
